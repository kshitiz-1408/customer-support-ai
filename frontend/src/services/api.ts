import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for handling clean error messages
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const customError = {
      message: error.response?.data?.detail || error.message || "An unexpected error occurred",
      status: error.response?.status,
      data: error.response?.data,
      requestId: error.response?.headers["x-request-id"] || error.response?.headers["X-Request-ID"] || null,
    };
    return Promise.reject(customError);
  }
);
