"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import styles from "./page.module.css";

// Interface definitions based on API schemas
interface Summary {
  id: number;
  document_id: number;
  summary_text: string;
  key_points?: string | null;
  created_at: string;
}

interface ChatMessage {
  id: number;
  document_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

interface Document {
  id: number;
  filename: string;
  file_type?: string | null;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  updated_at: string;
}

interface DocumentDetail extends Document {
  summaries: Summary[];
  chat_messages: ChatMessage[];
}

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export default function Home() {
  // Document States
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Active Selected Document
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [selectedDocDetail, setSelectedDocDetail] = useState<DocumentDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Right Panel Tabs: "summary" or "chat"
  const [activeTab, setActiveTab] = useState<"summary" | "chat">("summary");

  // Chat Q&A states
  const [chatQuestion, setChatQuestion] = useState<string>("");
  const [chatSending, setChatSending] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Search and Filters
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Upload States
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Authentication States
  const [token, setToken] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  
  // Auth Modal States: null, "login", "signup", "otp", "forgot_password", "reset_password"
  const [authModal, setAuthModal] = useState<string | null>(null);
  const [authEmail, setAuthEmail] = useState<string>("");
  const [authPassword, setAuthPassword] = useState<string>("");
  const [authOtpCode, setAuthOtpCode] = useState<string>("");
  const [authNewPassword, setAuthNewPassword] = useState<string>("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authSuccessMsg, setAuthSuccessMsg] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [showNewPassword, setShowNewPassword] = useState<boolean>(false);

  // Ref to track if we need to poll
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load token & user session on start
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedToken = localStorage.getItem("auth_token");
      const storedEmail = localStorage.getItem("auth_email");
      if (storedToken && storedEmail) {
        setToken(storedToken);
        setUserEmail(storedEmail);
      }
    }
  }, []);

  // Fetch all documents from API
  const fetchDocuments = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    
    const headers: HeadersInit = {};
    const storedToken = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (storedToken) {
      headers["Authorization"] = `Bearer ${storedToken}`;
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/documents/`, { headers });
      if (response.status === 401) {
        // Token invalid/expired - force logout
        handleLogout();
        return;
      }
      if (!response.ok) {
        throw new Error(`Failed to load documents: ${response.statusText}`);
      }
      const data = await response.json();
      setDocuments(data);
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError("Unable to connect to the backend services. Please ensure the backend server is running.");
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  // Fetch specific document details (with summaries and chat history)
  const fetchDocumentDetail = useCallback(async (docId: number) => {
    setLoadingDetail(true);
    
    const headers: HeadersInit = {};
    const storedToken = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (storedToken) {
      headers["Authorization"] = `Bearer ${storedToken}`;
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/documents/${docId}`, { headers });
      if (response.status === 401) {
        handleLogout();
        return;
      }
      if (!response.ok) {
        throw new Error(`Failed to fetch details: ${response.statusText}`);
      }
      const data: DocumentDetail = await response.json();
      setSelectedDocDetail(data);
      setChatMessages(data.chat_messages || []);
    } catch (err: any) {
      console.error(err);
      setUploadError("Could not retrieve document summary details.");
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  // Poll for document status updates if any document is pending/processing
  useEffect(() => {
    const hasActiveTasks = documents.some(
      (doc) => doc.status === "pending" || doc.status === "processing"
    );

    if (hasActiveTasks) {
      if (!pollIntervalRef.current) {
        pollIntervalRef.current = setInterval(() => {
          fetchDocuments(true);
          // If a document is currently selected and it's still processing, update its detail too
          if (selectedDocId) {
            const currentSelected = documents.find(d => d.id === selectedDocId);
            if (currentSelected && (currentSelected.status === "pending" || currentSelected.status === "processing")) {
              fetchDocumentDetail(selectedDocId);
            }
          }
        }, 3000);
      }
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [documents, selectedDocId, fetchDocuments, fetchDocumentDetail]);

  // Refetch when token changes
  useEffect(() => {
    fetchDocuments();
    setSelectedDocId(null);
    setSelectedDocDetail(null);
    setChatMessages([]);
  }, [token, fetchDocuments]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Handle document click
  const handleSelectDocument = (docId: number) => {
    setSelectedDocId(docId);
    fetchDocumentDetail(docId);
  };

  // Handle document delete
  const handleDeleteDocument = async (e: React.MouseEvent, docId: number) => {
    e.stopPropagation();
    console.log("handleDeleteDocument triggered for docId:", docId);

    let confirmed = false;
    if (typeof window !== "undefined") {
      confirmed = window.confirm("Are you sure you want to delete this document?");
    } else {
      confirmed = true;
    }

    console.log("Confirmation status:", confirmed);
    if (!confirmed) return;

    const headers: HeadersInit = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const deleteUrl = `${API_BASE}/api/v1/documents/${docId}`;
      console.log("Sending DELETE request to:", deleteUrl);
      
      const response = await fetch(deleteUrl, {
        method: "DELETE",
        headers: {
          ...headers,
          "Accept": "application/json"
        }
      });

      console.log("Delete API response status:", response.status);
      if (response.status === 401) {
        handleLogout();
        return;
      }
      if (!response.ok) {
        throw new Error(`Failed to delete document. Server status: ${response.status}`);
      }

      // If active document was deleted, reset details
      if (selectedDocId === docId) {
        setSelectedDocId(null);
        setSelectedDocDetail(null);
        setChatMessages([]);
      }

      // Optimistic state update
      setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
      console.log("Successfully deleted docId from state:", docId);
    } catch (err: any) {
      console.error("Delete document error:", err);
      alert(`Error: ${err.message}`);
    }
  };

  // Upload Logic
  const uploadFile = async (file: File) => {
    setUploadError(null);
    setUploadProgress(10);
    const formData = new FormData();
    formData.append("file", file);

    const headers: HeadersInit = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      setUploadProgress(30);
      const response = await fetch(`${API_BASE}/api/v1/documents/upload`, {
        method: "POST",
        headers,
        body: formData,
      });

      if (response.status === 401) {
        handleLogout();
        return;
      }

      if (!response.ok) {
        const errorDetail = await response.json().catch(() => ({}));
        throw new Error(errorDetail.detail || "Upload failed. Please check guest limits or backend logs.");
      }

      setUploadProgress(100);
      const newDoc = await response.json();
      
      // Update document list and select the new document
      setDocuments((prev) => [newDoc, ...prev]);
      setSelectedDocId(newDoc.id);
      setSelectedDocDetail({ ...newDoc, summaries: [], chat_messages: [] });
      setChatMessages([]);
      setActiveTab("summary");

      // Trigger automatic background polling immediately
      fetchDocuments(true);

      setTimeout(() => {
        setUploadProgress(null);
      }, 1500);

    } catch (err: any) {
      console.error(err);
      setUploadError(err.message || "Failed to upload file.");
      setUploadProgress(null);
    }
  };

  // Q&A Chat Submit
  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatQuestion.trim() || !selectedDocId || !token) return;

    const question = chatQuestion.trim();
    setChatQuestion("");
    setChatSending(true);

    // Optimistically add user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      document_id: selectedDocId,
      role: "user",
      content: question,
      created_at: new Date().toISOString()
    };
    setChatMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await fetch(`${API_BASE}/api/v1/documents/${selectedDocId}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ content: question })
      });

      if (response.status === 401) {
        handleLogout();
        return;
      }

      if (!response.ok) {
        const errorDetail = await response.json().catch(() => ({}));
        throw new Error(errorDetail.detail || "Failed to get response from AI model.");
      }

      const aiMsg: ChatMessage = await response.json();
      setChatMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      console.error(err);
      // Append error message to chat
      const errorMsg: ChatMessage = {
        id: Date.now() + 1,
        document_id: selectedDocId,
        role: "assistant",
        content: `❌ Error: ${err.message || "Unable to retrieve chat response."}`,
        created_at: new Date().toISOString()
      };
      setChatMessages((prev) => [...prev, errorMsg]);
    } finally {
      setChatSending(false);
    }
  };

  // Authentication Logic: Manual Sign Out
  const handleLogout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_email");
    }
    setToken(null);
    setUserEmail(null);
    setSelectedDocId(null);
    setSelectedDocDetail(null);
    setChatMessages([]);
  };

  // Open Auth Modal
  const openAuth = (mode: string) => {
    setAuthModal(mode);
    setAuthEmail("");
    setAuthPassword("");
    setAuthOtpCode("");
    setAuthNewPassword("");
    setAuthError(null);
    setAuthSuccessMsg(null);
    setShowPassword(false);
    setShowNewPassword(false);
  };

  // Auth Form Submission
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);

    try {
      if (authModal === "login") {
        const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: authEmail, password: authPassword })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Login failed.");

        localStorage.setItem("auth_token", data.access_token);
        localStorage.setItem("auth_email", data.email);
        setToken(data.access_token);
        setUserEmail(data.email);
        setAuthModal(null);

      } else if (authModal === "signup") {
        const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: authEmail, password: authPassword })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Registration failed.");

        // Switch to OTP verification modal
        setAuthModal("otp");
        setAuthSuccessMsg("We sent a verification code to your email. Please enter it below.");

      } else if (authModal === "otp") {
        const response = await fetch(`${API_BASE}/api/v1/auth/verify-registration`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: authEmail, otp_code: authOtpCode })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "OTP verification failed.");

        localStorage.setItem("auth_token", data.access_token);
        localStorage.setItem("auth_email", data.email);
        setToken(data.access_token);
        setUserEmail(data.email);
        setAuthModal(null);

      } else if (authModal === "forgot_password") {
        const response = await fetch(`${API_BASE}/api/v1/auth/password-reset-request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: authEmail })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Password reset request failed.");

        setAuthModal("reset_password");
        setAuthSuccessMsg("If the email is registered, we sent a password reset OTP code. Enter it below.");

      } else if (authModal === "reset_password") {
        const response = await fetch(`${API_BASE}/api/v1/auth/password-reset-confirm`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: authEmail,
            otp_code: authOtpCode,
            new_password: authNewPassword
          })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Password reset confirmation failed.");

        setAuthModal("login");
        setAuthSuccessMsg("Password updated successfully. You can now log in.");
      }
    } catch (err: any) {
      setAuthError(err.message || "An authentication error occurred.");
    } finally {
      setAuthLoading(false);
    }
  };

  // Google OAuth Login Verification Callback
  const handleGoogleCallback = async (idToken: string) => {
    setAuthError(null);
    setAuthLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: idToken })
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Google authentication failed.");

      localStorage.setItem("auth_token", data.access_token);
      localStorage.setItem("auth_email", data.email);
      setToken(data.access_token);
      setUserEmail(data.email);
      setAuthModal(null);
    } catch (err: any) {
      console.error(err);
      setAuthError(err.message || "Google sign-in verification failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  // Dynamically initialize Google OAuth Button inside the modal DOM
  useEffect(() => {
    if (typeof window !== "undefined" && (authModal === "login" || authModal === "signup")) {
      const initGoogle = () => {
        const win = window as any;
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
        if (win.google?.accounts?.id) {
          if (!clientId) {
            console.warn("Google Client ID is missing. Please configure NEXT_PUBLIC_GOOGLE_CLIENT_ID in your env variables.");
            return;
          }
          win.google.accounts.id.initialize({
            client_id: clientId,
            callback: (response: any) => {
              handleGoogleCallback(response.credential);
            }
          });
          const btnDiv = document.getElementById("google-signin-btn");
          if (btnDiv) {
            win.google.accounts.id.renderButton(btnDiv, {
              theme: "outline",
              size: "large",
              width: "100%"
            });
          }
        }
      };

      const t = setTimeout(initGoogle, 200);
      return () => clearTimeout(t);
    }
  }, [authModal]);

  // Drag and Drop Handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!token && documents.length >= 3) return; // ignore drag if limit reached
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setUploadError(null);

    // Enforce limits
    if (!token && documents.length >= 3) {
      setUploadError("Guest limit reached (max 3 uploads). Please login or sign up.");
      return;
    }

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    if (!token && documents.length >= 3) {
      setUploadError("Guest limit reached (max 3 uploads). Please login or sign up.");
      return;
    }

    const files = e.target.files;
    if (files && files.length > 0) {
      uploadFile(files[0]);
    }
  };

  const triggerFileInput = () => {
    if (!token && documents.length >= 3) {
      setUploadError("Guest limit reached (max 3 uploads). Please login or sign up.");
      return;
    }
    fileInputRef.current?.click();
  };

  // Helper formatting functions
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  // Filters mapping
  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Dynamic statistics
  const totalCount = documents.length;
  const completedCount = documents.filter((d) => d.status === "completed").length;
  const processingCount = documents.filter((d) => d.status === "processing" || d.status === "pending").length;
  const failedCount = documents.filter((d) => d.status === "failed").length;

  return (
    <div className={styles.container}>
      {/* Premium Header */}
      <header className={styles.header}>
        <div className={styles.logoArea}>
          <div className={styles.logoIcon}>LS</div>
          <div className={styles.titleGroup}>
            <h1>LogStream AI</h1>
            <p>Intelligent Document & Log Summarizer</p>
          </div>
        </div>

        {/* User Session Info */}
        <div className={styles.headerUser}>
          {token && userEmail ? (
            <>
              <span className={styles.userEmail}>Signed in as: <strong>{userEmail}</strong></span>
              <button className={styles.logoutBtn} onClick={handleLogout}>Sign Out</button>
            </>
          ) : (
            <button className={styles.loginBtn} onClick={() => openAuth("login")}>Sign In / Sign Up</button>
          )}
        </div>
      </header>

      {/* Grid Dashboard */}
      <main className={styles.dashboard}>
        {/* Left Side: Upload & File management */}
        <section className={styles.leftPanel}>
          
          {/* Guest Limit Notification Banner */}
          {!token && (
            <div className={styles.limitBanner}>
              <span>
                🔒 Guest Mode: <strong>{3 - totalCount > 0 ? 3 - totalCount : 0} of 3</strong> uploads remaining.
              </span>
              <span className={styles.limitRegisterLink} onClick={() => openAuth("signup")}>
                Sign up for unlimited uploads & Chat Q&A!
              </span>
            </div>
          )}

          {/* Drag & Drop Upload Zone */}
          <div 
            className={`${styles.uploadZone} ${isDragging ? styles.uploadZoneDragging : ""} ${(!token && documents.length >= 3) ? styles.uploadZoneDisabled : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={triggerFileInput}
            style={(!token && documents.length >= 3) ? { opacity: 0.5, cursor: "not-allowed", borderStyle: "solid" } : {}}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: "none" }} 
              onChange={handleFileSelect}
              accept=".log,.txt,.pdf,.docx,.doc,text/*"
              disabled={!token && documents.length >= 3}
            />
            <div className={styles.uploadIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div className={styles.uploadText}>
              {(!token && documents.length >= 3) ? (
                <h3>Upload limit reached. Please register to continue.</h3>
              ) : (
                <h3>Drag & Drop files here or click to upload</h3>
              )}
              <p>Supports .log, .txt, .pdf, and .docx files</p>
            </div>
            {uploadProgress !== null && (
              <div className={styles.progressContainer}>
                <div className={styles.progressBar} style={{ width: `${uploadProgress}%` }} />
              </div>
            )}
            {uploadError && (
              <p style={{ color: "var(--danger)", fontSize: "12px", marginTop: "8px", fontWeight: 500 }}>
                {uploadError}
              </p>
            )}
          </div>

          {/* Search, filters, controls */}
          <div className={styles.controls}>
            <input 
              type="text" 
              placeholder="Search documents..." 
              className={styles.searchInput}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <select 
              className={styles.filterSelect}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          {/* File list container */}
          <div className={styles.listContainer}>
            <div className={styles.listHeader}>
              <h2>Uploaded Documents ({totalCount})</h2>
              <button className={styles.refreshButton} onClick={() => fetchDocuments(false)}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                </svg>
                Sync Status
              </button>
            </div>

            {loading ? (
              <div style={{ textAlign: "center", padding: "40px", color: "var(--text-secondary)" }}>
                <span className={`${styles.spinnerSmall} animate-spin`} style={{ width: "24px", height: "24px", borderWidth: "3px" }} />
                <p style={{ marginTop: "12px" }}>Loading logs and documents...</p>
              </div>
            ) : error ? (
              <div style={{ padding: "20px", color: "var(--danger)", border: "1px solid var(--danger-border)", borderRadius: "8px", background: "var(--danger-glow)" }}>
                <p>{error}</p>
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className={styles.emptyState}>
                {searchTerm || statusFilter !== "all" 
                  ? "No documents match your active filters." 
                  : "No documents uploaded yet. Drop a log file above to get started!"}
              </div>
            ) : (
              <div className={styles.docList}>
                {filteredDocuments.map((doc) => {
                  const isActive = doc.id === selectedDocId;
                  return (
                    <div 
                      key={doc.id}
                      className={`${styles.docCard} ${isActive ? styles.docCardActive : ""}`}
                      onClick={() => handleSelectDocument(doc.id)}
                    >
                      <div className={styles.docInfo}>
                        <h4 className={styles.docTitle} title={doc.filename}>{doc.filename}</h4>
                        <div className={styles.docMeta}>
                          <span>{doc.file_type ? doc.file_type.split("/")[1]?.toUpperCase() || "LOG" : "LOG"}</span>
                          <span className={styles.bulletSeparator}>•</span>
                          <span>{formatDate(doc.created_at)}</span>
                        </div>
                      </div>

                      <div className={styles.statusWrapper}>
                        {doc.status === "pending" && (
                          <span className={`${styles.statusBadge} ${styles.statusPending}`}>Pending</span>
                        )}
                        {doc.status === "processing" && (
                          <span className={`${styles.statusBadge} ${styles.statusProcessing}`}>
                            <span className={`${styles.spinnerSmall} animate-spin`} />
                            Processing
                          </span>
                        )}
                        {doc.status === "completed" && (
                          <span className={`${styles.statusBadge} ${styles.statusCompleted}`}>Ready</span>
                        )}
                        {doc.status === "failed" && (
                          <span className={`${styles.statusBadge} ${styles.statusFailed}`}>Failed</span>
                        )}

                        <button 
                          className={styles.deleteButton} 
                          onClick={(e) => handleDeleteDocument(e, doc.id)}
                          title="Delete document"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            <line x1="10" y1="11" x2="10" y2="17" />
                            <line x1="14" y1="11" x2="14" y2="17" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        {/* Right Side: Detailed summary viewer / Q&A chat */}
        <section className={styles.rightPanel}>
          {selectedDocId === null ? (
            <div className={styles.detailEmpty}>
              <div className={styles.detailEmptyIcon}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <line x1="10" y1="9" x2="8" y2="9" />
                </svg>
              </div>
              <h3>No Log Selected</h3>
              <p>Select a document from the list on the left to see its AI summary and structured insights.</p>
            </div>
          ) : loadingDetail ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, color: "var(--text-secondary)", marginTop: "120px" }}>
              <span className={`${styles.spinnerSmall} animate-spin`} style={{ width: "32px", height: "32px", borderWidth: "3px" }} />
              <p style={{ marginTop: "16px", fontSize: "14px" }}>Retrieving executive summary...</p>
            </div>
          ) : selectedDocDetail ? (
            <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
              {/* Tab Header Selector */}
              <div className={styles.tabHeader}>
                <button 
                  className={`${styles.tabBtn} ${activeTab === "summary" ? styles.tabBtnActive : ""}`}
                  onClick={() => setActiveTab("summary")}
                >
                  Summary
                </button>
                <button 
                  className={`${styles.tabBtn} ${activeTab === "chat" ? styles.tabBtnActive : ""}`}
                  onClick={() => setActiveTab("chat")}
                >
                  Interactive Q&A Chat
                </button>
              </div>

              {/* Tab Content 1: Summary Insights */}
              {activeTab === "summary" && (
                <div className={`${styles.detailContent} animate-fade-in`}>
                  <div className={styles.detailHeader}>
                    <div className={styles.detailTitleArea}>
                      <h2 className={styles.detailTitle}>{selectedDocDetail.filename}</h2>
                      <div className={styles.detailMeta}>
                        <span>Uploaded: {formatDate(selectedDocDetail.created_at)}</span>
                        <span className={styles.bulletSeparator} style={{ margin: "0 6px" }}>•</span>
                        <span>Status: {selectedDocDetail.status.toUpperCase()}</span>
                      </div>
                    </div>
                  </div>

                  {selectedDocDetail.status === "pending" || selectedDocDetail.status === "processing" ? (
                    <div style={{ padding: "40px 20px", textAlign: "center", background: "rgba(255, 255, 255, 0.01)", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
                      <span className={`${styles.spinnerSmall} animate-spin`} style={{ width: "24px", height: "24px", color: "var(--info)", marginBottom: "12px" }} />
                      <h4>Generating AI Summary...</h4>
                      <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                        This happens in the background. Once the analysis completes, the summary will automatically display.
                      </p>
                    </div>
                  ) : selectedDocDetail.status === "failed" ? (
                    <div style={{ padding: "30px 20px", textAlign: "center", background: "var(--danger-glow)", border: "1px solid var(--danger-border)", borderRadius: "8px" }}>
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: "8px" }}>
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      <h4 style={{ color: "var(--danger)" }}>Summarization Failed</h4>
                      <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                        We were unable to parse or summarize this file. Check the backend logs for details.
                      </p>
                    </div>
                  ) : selectedDocDetail.summaries && selectedDocDetail.summaries.length > 0 ? (
                    <>
                      <div className={styles.section}>
                        <h3>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--info)" }}>
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                            <line x1="16" y1="13" x2="8" y2="13" />
                            <line x1="16" y1="17" x2="8" y2="17" />
                            <polyline points="10 9 9 9 8 9" />
                          </svg>
                          Executive Summary
                        </h3>
                        <div className={styles.summaryBox}>
                          {selectedDocDetail.summaries[0].summary_text}
                        </div>
                      </div>

                      {selectedDocDetail.summaries[0].key_points && (
                        <div className={styles.section}>
                          <h3>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--primary)" }}>
                              <line x1="9" y1="6" x2="20" y2="6" />
                              <line x1="9" y1="12" x2="20" y2="12" />
                              <line x1="9" y1="18" x2="20" y2="18" />
                              <line x1="5" y1="6" x2="5.01" y2="6" />
                              <line x1="5" y1="12" x2="5.01" y2="12" />
                              <line x1="5" y1="18" x2="5.01" y2="18" />
                            </svg>
                            Key Points & Takeaways
                          </h3>
                          <div className={styles.keyPointsBox}>
                            <ul>
                              {selectedDocDetail.summaries[0].key_points
                                .split("\n")
                                .filter((line) => line.trim().startsWith("-") || line.trim().startsWith("*"))
                                .map((line, idx) => {
                                  const cleanedLine = line.replace(/^[\s-*]+/, "").trim();
                                  const boldMatch = cleanedLine.match(/^\*\*(.*?)\*\*(.*)/);
                                  if (boldMatch) {
                                    return (
                                      <li key={idx}>
                                        <strong>{boldMatch[1]}</strong>{boldMatch[2]}
                                      </li>
                                    );
                                  }
                                  return <li key={idx}>{cleanedLine}</li>;
                                })}
                            </ul>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div style={{ padding: "40px 20px", textAlign: "center", background: "rgba(255, 255, 255, 0.01)", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
                      <h4>No summaries generated yet.</h4>
                    </div>
                  )}
                </div>
              )}

              {/* Tab Content 2: Interactive Q&A Chat */}
              {activeTab === "chat" && (
                <div className={`${styles.chatContainer} animate-fade-in`}>
                  {!token ? (
                    /* Locked Chat state for Guests */
                    <div className={styles.chatAuthPrompt}>
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--warning)" }}>
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                      <h3>Interactive Q&A is Locked</h3>
                      <p>
                        Asking follow-up questions about this log file requires an account. 
                        Register for free to unlock contextual conversation, history saving, and unlimited uploads!
                      </p>
                      <button className={styles.chatAuthBtn} onClick={() => openAuth("login")}>Sign In / Sign Up Now</button>
                    </div>
                  ) : (
                    /* Active Chat Session */
                    <>
                      <div className={styles.chatMessages}>
                        {chatMessages.length === 0 ? (
                          <div className={styles.chatEmpty}>
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                            </svg>
                            <h4>Ask follow-up questions</h4>
                            <p style={{ fontSize: "12px" }}>
                              Ask details like "What caused the error?", "Give me a list of warnings", or "How can I fix it?"
                            </p>
                          </div>
                        ) : (
                          chatMessages.map((msg) => (
                            <div 
                              key={msg.id} 
                              className={`${styles.messageRow} ${msg.role === "user" ? styles.messageRowUser : styles.messageRowAssistant}`}
                            >
                              <div className={`${styles.messageBubble} ${msg.role === "user" ? styles.messageBubbleUser : styles.messageBubbleAssistant}`}>
                                {msg.content.startsWith("**[Offline Fallback Answer]**") ? (
                                  /* Render matching sentences fallback neatly */
                                  <div>
                                    <strong style={{ color: "var(--warning)", display: "block", marginBottom: "8px" }}>Offline Fallback Q&A</strong>
                                    {msg.content.replace("**[Offline Fallback Answer]**", "").trim().split("\n\n").map((chunk, cIdx) => (
                                      <p key={cIdx} style={{ marginBottom: "8px" }}>{chunk}</p>
                                    ))}
                                  </div>
                                ) : (
                                  msg.content.split("\n").map((line, lIdx) => (
                                    <div key={lIdx}>{line}</div>
                                  ))
                                )}
                              </div>
                            </div>
                          ))
                        )}
                        {chatSending && (
                          <div className={`${styles.messageRow} ${styles.messageRowAssistant}`}>
                            <div className={`${styles.messageBubble} ${styles.messageBubbleAssistant}`} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span className={`${styles.spinnerSmall} animate-spin`} />
                              <span>AI is reading log context...</span>
                            </div>
                          </div>
                        )}
                        <div ref={chatBottomRef} />
                      </div>

                      {/* Chat Footer Input form */}
                      <div className={styles.chatInputArea}>
                        <form onSubmit={handleSendChat} className={styles.chatInputForm}>
                          <input 
                            type="text" 
                            placeholder="Ask a question about this log..." 
                            className={styles.chatInput}
                            value={chatQuestion}
                            onChange={(e) => setChatQuestion(e.target.value)}
                            disabled={chatSending}
                          />
                          <button 
                            type="submit" 
                            className={styles.chatSendBtn}
                            disabled={!chatQuestion.trim() || chatSending}
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <line x1="22" y1="2" x2="11" y2="13" />
                              <polyline points="22 2 15 22 11 13 2 9 22 2" />
                            </svg>
                          </button>
                        </form>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ) : null}
        </section>
      </main>

      {/* Unified Authentication Modals Overlay */}
      {authModal && (
        <div className={styles.modalOverlay} onClick={() => setAuthModal(null)}>
          <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              {authModal === "login" && (
                <>
                  <h2>Welcome Back</h2>
                  <p>Login to save history, Q&A chat, and get unlimited uploads.</p>
                </>
              )}
              {authModal === "signup" && (
                <>
                  <h2>Create Account</h2>
                  <p>Register to unlock unlimited file uploads and interactive chat.</p>
                </>
              )}
              {authModal === "otp" && (
                <>
                  <h2>Verify Email OTP</h2>
                  <p>Enter the 6-digit code sent to <strong>{authEmail}</strong></p>
                </>
              )}
              {authModal === "forgot_password" && (
                <>
                  <h2>Reset Password</h2>
                  <p>Enter your email and we'll send you a password reset code.</p>
                </>
              )}
              {authModal === "reset_password" && (
                <>
                  <h2>Reset Password Code</h2>
                  <p>Enter the OTP reset code and configure your new password.</p>
                </>
              )}
            </div>

            {authSuccessMsg && (
              <div style={{ color: "var(--success)", background: "var(--success-glow)", border: "1px solid var(--success-border)", padding: "10px", borderRadius: "6px", fontSize: "12px" }}>
                {authSuccessMsg}
              </div>
            )}

            {authError && (
              <div className={styles.authError}>
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className={styles.authForm}>
              {/* Email Input for Login, Signup, Forgot Password, Reset Password */}
              {(authModal === "login" || authModal === "signup" || authModal === "forgot_password" || authModal === "reset_password") && (
                <div className={styles.formGroup}>
                  <label htmlFor="auth-email">Email Address</label>
                  <input 
                    id="auth-email"
                    type="email" 
                    className={styles.formInput} 
                    placeholder="name@company.com"
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    required
                    disabled={authLoading || authModal === "reset_password"}
                  />
                </div>
              )}

              {/* Password Input for Login, Signup */}
              {(authModal === "login" || authModal === "signup") && (
                <div className={styles.formGroup}>
                  <label htmlFor="auth-password">Password</label>
                  <div className={styles.passwordInputWrapper}>
                    <input 
                      id="auth-password"
                      type={showPassword ? "text" : "password"} 
                      className={styles.formInput} 
                      placeholder="••••••••"
                      value={authPassword}
                      onChange={(e) => setAuthPassword(e.target.value)}
                      required
                      disabled={authLoading}
                    />
                    <button
                      type="button"
                      className={styles.passwordToggleBtn}
                      onClick={() => setShowPassword(!showPassword)}
                      title={showPassword ? "Hide password" : "Show password"}
                      tabIndex={-1}
                    >
                      {showPassword ? (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </svg>
                      ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* OTP code Input for Verification, Reset Confirm */}
              {(authModal === "otp" || authModal === "reset_password") && (
                <div className={styles.formGroup}>
                  <label htmlFor="auth-otp">6-Digit OTP Verification Code</label>
                  <input 
                    id="auth-otp"
                    type="text" 
                    maxLength={6}
                    className={styles.formInput} 
                    placeholder="123456"
                    value={authOtpCode}
                    onChange={(e) => setAuthOtpCode(e.target.value)}
                    required
                    disabled={authLoading}
                    style={{ textAlign: "center", fontSize: "20px", letterSpacing: "8px" }}
                  />
                </div>
              )}

              {/* New Password Input for Reset Confirm */}
              {authModal === "reset_password" && (
                <div className={styles.formGroup}>
                  <label htmlFor="auth-new-password">Choose New Password</label>
                  <div className={styles.passwordInputWrapper}>
                    <input 
                      id="auth-new-password"
                      type={showNewPassword ? "text" : "password"} 
                      className={styles.formInput} 
                      placeholder="••••••••"
                      value={authNewPassword}
                      onChange={(e) => setAuthNewPassword(e.target.value)}
                      required
                      disabled={authLoading}
                    />
                    <button
                      type="button"
                      className={styles.passwordToggleBtn}
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      title={showNewPassword ? "Hide password" : "Show password"}
                      tabIndex={-1}
                    >
                      {showNewPassword ? (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </svg>
                      ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {authModal === "login" && (
                <div style={{ textAlign: "right", marginTop: "-6px" }}>
                  <span className={styles.authFooterLink} style={{ fontSize: "12px" }} onClick={() => openAuth("forgot_password")}>
                    Forgot password?
                  </span>
                </div>
              )}

              <div className={styles.authActionRow}>
                <button type="button" className={styles.authCancelBtn} onClick={() => setAuthModal(null)} disabled={authLoading}>
                  Cancel
                </button>
                <button type="submit" className={styles.authSubmitBtn} disabled={authLoading}>
                  {authLoading ? (
                    <span className={`${styles.spinnerSmall} animate-spin`} />
                  ) : authModal === "login" ? (
                    "Sign In"
                  ) : authModal === "signup" ? (
                    "Register & Send OTP"
                  ) : authModal === "otp" || authModal === "reset_password" ? (
                    "Verify & Activate"
                  ) : (
                    "Submit Request"
                  )}
                </button>
              </div>
            </form>

            {/* Social Oauth / Login Switch footer */}
            {(authModal === "login" || authModal === "signup") && (
              <>
                <div className={styles.divider}>or</div>
                
                {/* Google Sign In mounting button */}
                <div id="google-signin-btn" className={styles.googleContainer}></div>
                
                <div className={styles.authFooter}>
                  {authModal === "login" ? (
                    <p>
                      Don't have an account?{" "}
                      <span className={styles.authFooterLink} onClick={() => openAuth("signup")}>
                        Create one now
                      </span>
                    </p>
                  ) : (
                    <p>
                      Already have an account?{" "}
                      <span className={styles.authFooterLink} onClick={() => openAuth("login")}>
                        Sign in instead
                      </span>
                    </p>
                  )}
                </div>
              </>
            )}

            {authModal === "forgot_password" && (
              <div className={styles.authFooter}>
                <p>
                  Remembered your credentials?{" "}
                  <span className={styles.authFooterLink} onClick={() => openAuth("login")}>
                    Back to login
                  </span>
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
