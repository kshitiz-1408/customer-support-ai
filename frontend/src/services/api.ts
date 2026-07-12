import axios from "axios";

const envApiUrl = process.env.NEXT_PUBLIC_API_URL;

export const api = axios.create({
  baseURL: `${envApiUrl || "http://localhost:8000"}/api/v1`,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to enforce environment constraints
api.interceptors.request.use(
  (config) => {
    const isProd = process.env.NODE_ENV === "production";
    const currentApiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (isProd && !currentApiUrl) {
      throw new Error(
        "NEXT_PUBLIC_API_URL is missing or empty in production! Please configure the backend API URL."
      );
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to normalize errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // If it's a cancelled request, handle it gracefully
    if (axios.isCancel(error)) {
      return Promise.reject({
        message: "Request was cancelled.",
        isCancelled: true,
        status: null,
        requestId: null,
      });
    }

    let errorMessage = "An unexpected error occurred.";
    let errorStatus = error.response?.status || null;
    const requestId = error.response?.headers?.["x-request-id"] || error.response?.headers?.["X-Request-ID"] || null;

    if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      errorMessage = "Request timed out. The backend server took too long to respond. Please try again.";
      errorStatus = 408;
    } else if (error.message === "Network Error") {
      errorMessage = "Could not connect to the backend server. Please verify the FastAPI service is online and reachable.";
    } else if (error.response?.status === 500) {
      errorMessage = "Internal Server Error occurred on the backend. Please check backend logs.";
    } else if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      if (typeof detail === "string") {
        errorMessage = detail;
      } else if (Array.isArray(detail)) {
        // Standard FastAPI validation error structure
        errorMessage = `Validation error: ${detail.map(d => `${d.loc?.join(".") || "field"}: ${d.msg}`).join("; ")}`;
      } else {
        errorMessage = JSON.stringify(detail);
      }
    } else if (error.message) {
      errorMessage = error.message;
    }

    const customError = {
      message: errorMessage,
      status: errorStatus,
      data: error.response?.data || null,
      requestId: requestId,
    };

    return Promise.reject(customError);
  }
);
