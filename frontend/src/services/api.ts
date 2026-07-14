import axios from "axios";

const envApiUrl = process.env.NEXT_PUBLIC_API_URL;

export const api = axios.create({
  baseURL: `${envApiUrl || "http://localhost:8000"}/api/v1`,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

interface FailedRequest {
  resolve: (token: string | null) => void;
  reject: (error: unknown) => void;
}

let isRefreshing = false;
let failedQueue: FailedRequest[] = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Request interceptor to enforce environment constraints and inject access token
api.interceptors.request.use(
  (config) => {
    const isProd = process.env.NODE_ENV === "production";
    const currentApiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (isProd && !currentApiUrl) {
      throw new Error(
        "NEXT_PUBLIC_API_URL is missing or empty in production! Please configure the backend API URL."
      );
    }
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("accessToken");
      if (token) {
        config.headers["Authorization"] = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh and normalize errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // If it's a cancelled request, handle it gracefully
    if (axios.isCancel(error)) {
      return Promise.reject({
        message: "Request was cancelled.",
        isCancelled: true,
        status: null,
        requestId: null,
      });
    }

    const originalRequest = error.config;
    const errorStatus = error.response?.status || null;

    // Check if error status is 401 Unauthorized and not already retried
    if (errorStatus === 401 && originalRequest && !originalRequest._retry) {
      const url = originalRequest.url || "";
      if (url.includes("/auth/login") || url.includes("/auth/register") || url.includes("/auth/refresh")) {
        // Skip retry for auth endpoints to prevent loops
      } else {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              originalRequest.headers["Authorization"] = `Bearer ${token}`;
              return api(originalRequest);
            })
            .catch((err) => Promise.reject(err));
        }

        originalRequest._retry = true;
        isRefreshing = true;

        if (typeof window !== "undefined") {
          const refreshToken = localStorage.getItem("refreshToken");
          if (!refreshToken) {
            isRefreshing = false;
            window.dispatchEvent(new Event("auth-logout"));
          } else {
            try {
              const envApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
              const res = await axios.post(`${envApiUrl}/api/v1/auth/refresh`, {
                refresh_token: refreshToken
              });
              const newAccessToken = res.data.access_token;
              localStorage.setItem("accessToken", newAccessToken);
              api.defaults.headers.common["Authorization"] = `Bearer ${newAccessToken}`;
              originalRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
              processQueue(null, newAccessToken);
              isRefreshing = false;
              return api(originalRequest);
            } catch (refreshError) {
              processQueue(refreshError, null);
              isRefreshing = false;
              localStorage.removeItem("accessToken");
              localStorage.removeItem("refreshToken");
              window.dispatchEvent(new Event("auth-logout"));
              error = refreshError;
            }
          }
        }
      }
    }

    let errorMessage = "An unexpected error occurred.";
    const requestId = error.response?.headers?.["x-request-id"] || error.response?.headers?.["X-Request-ID"] || null;

    if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      errorMessage = "Request timed out. The backend server took too long to respond. Please try again.";
    } else if (error.message === "Network Error") {
      errorMessage = "Could not connect to the backend server. Please verify the FastAPI service is online and reachable.";
    } else if (error.response?.status === 500) {
      errorMessage = "Internal Server Error occurred on the backend. Please check backend logs.";
    } else if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      if (typeof detail === "string") {
        errorMessage = detail;
      } else if (Array.isArray(detail)) {
        errorMessage = `Validation error: ${detail.map(d => `${d.loc?.join(".") || "field"}: ${d.msg}`).join("; ")}`;
      } else {
        errorMessage = JSON.stringify(detail);
      }
    } else if (error.message) {
      errorMessage = error.message;
    }

    const customError = {
      message: errorMessage,
      status: error.response?.status || errorStatus,
      data: error.response?.data || null,
      requestId: requestId,
    };

    return Promise.reject(customError);
  }
);
