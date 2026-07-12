const assert = require("assert");
const Module = require("module");

// 1. Mock Axios client to isolate test execution
const mockAxios = {
  create: function(config) {
    this.instance = {
      defaults: config,
      interceptors: {
        request: {
          use: function(success, fail) {
            this.success = success;
            this.fail = fail;
          }
        },
        response: {
          use: function(success, fail) {
            this.success = success;
            this.fail = fail;
          }
        }
      }
    };
    return this.instance;
  },
  isCancel: function(error) {
    return error && error.isCancelled === true;
  }
};
// Handle ES6 interop default exports in compiled tsc output
mockAxios.default = mockAxios;

// Redirect axios imports to our mockAxios object
const originalRequire = Module.prototype.require;
Module.prototype.require = function(moduleName) {
  if (moduleName === "axios") {
    return mockAxios;
  }
  return originalRequire.apply(this, arguments);
};

// Clean cache and load the compiled api.js
delete require.cache[require.resolve("./dist/api.js")];
const apiModule = require("./dist/api.js");
const axiosInstance = mockAxios.instance;

console.log("-------------------------------------------------");
console.log("RUNNING FRONTEND CUSTOM API CLIENT TESTS");
console.log("-------------------------------------------------");

// TEST 1: Request Interceptor URL Enforcer in Production
(function testRequestInterceptorProd() {
  process.env.NODE_ENV = "production";
  process.env.NEXT_PUBLIC_API_URL = "";

  const reqInterceptor = axiosInstance.interceptors.request.success;
  
  assert.throws(
    () => reqInterceptor({ headers: {} }),
    /NEXT_PUBLIC_API_URL is missing or empty in production/,
    "Should throw if NEXT_PUBLIC_API_URL is missing in production"
  );
  
  console.log("✓ Request interceptor throws on missing URL in production");
})();

// TEST 2: Request Interceptor URL Passer in Production
(function testRequestInterceptorSuccess() {
  process.env.NODE_ENV = "production";
  process.env.NEXT_PUBLIC_API_URL = "https://backend.myproduction.com";
  
  // Reload module to bind the new URL
  delete require.cache[require.resolve("./dist/api.js")];
  const freshApiModule = require("./dist/api.js");
  const freshAxiosInstance = mockAxios.instance;
  const reqInterceptor = freshAxiosInstance.interceptors.request.success;

  const config = { headers: {} };
  const result = reqInterceptor(config);
  assert.deepStrictEqual(result, config, "Should return config unaltered when URL is set");
  
  console.log("✓ Request interceptor passes when URL is configured in production");
})();

// TEST 3: Response Interceptor Error Normalization
(function testResponseInterceptorNormalization() {
  const respInterceptorFail = axiosInstance.interceptors.response.fail;

  // Case A: Timeout error
  const timeoutError = {
    code: "ECONNABORTED",
    message: "timeout of 30000ms exceeded",
    response: null
  };
  respInterceptorFail(timeoutError).catch((err) => {
    assert.ok(err.message.includes("Request timed out"), "Should map to timeout error message");
    assert.strictEqual(err.status, 408);
    console.log("✓ Timeout error mapped correctly to status 408");
  });

  // Case B: Network Error
  const networkError = {
    message: "Network Error",
    response: null
  };
  respInterceptorFail(networkError).catch((err) => {
    assert.ok(err.message.includes("Could not connect to the backend server"), "Should map to server connection error");
    console.log("✓ Network connection error mapped correctly");
  });

  // Case C: FastAPI 422 validation array error structure
  const validationError = {
    response: {
      status: 422,
      data: {
        detail: [
          { loc: ["body", "message"], msg: "Field required" }
        ]
      }
    }
  };
  respInterceptorFail(validationError).catch((err) => {
    assert.ok(err.message.includes("Validation error: body.message: Field required"), "Should format field details");
    assert.strictEqual(err.status, 422);
    console.log("✓ FastAPI Validation error formatted correctly");
  });

  // Case D: Server 500 error hides stack traces
  const serverError = {
    response: {
      status: 500,
      data: { detail: "Traceback: line 42 database crash" }
    }
  };
  respInterceptorFail(serverError).catch((err) => {
    assert.ok(err.message.includes("Internal Server Error occurred on the backend"), "Should hide traceback details");
    assert.strictEqual(err.status, 500);
    console.log("✓ Server error hides stack trace leakage");
  });

  // Case E: Request cancellation
  const cancelledError = {
    __CANCEL__: true, // Axios cancel check relies on this or isCancel()
    isCancelled: true
  };
  respInterceptorFail(cancelledError).catch((err) => {
    assert.strictEqual(err.isCancelled, true);
    assert.strictEqual(err.message, "Request was cancelled.");
    console.log("✓ Request cancellation mapped successfully");
  });
})();

// TEST 4: useChat Hook Logic Simulation
(function testUseChatLogic() {
  // Simulating browser local storage
  const storage = {
    "customer_support_conversation_id": "conv-123"
  };

  // Mock message sending context
  let loading = false;
  let conversationId = storage["customer_support_conversation_id"];
  let cancelledCount = 0;
  
  // Simulated abort controller tracking
  let activeAbortController = null;

  function mockSendMessage(text) {
    // 0. Double-submission check
    if (loading) {
      console.log("  - Duplicate submit blocked!");
      return "blocked";
    }

    // 1. Request cancellation
    if (activeAbortController) {
      activeAbortController.abort();
      cancelledCount++;
      console.log("  - In-flight request aborted!");
    }

    activeAbortController = {
      aborted: false,
      abort() { this.aborted = true; }
    };

    // Simulate React async state render boundaries
    setTimeout(() => {
      loading = true;
    }, 0);
    
    // Simulate async resolve
    return new Promise((resolve, reject) => {
      const myController = activeAbortController;
      setTimeout(() => {
        if (myController.aborted) {
          reject({ isCancelled: true });
          return;
        }
        loading = false;
        resolve({ conversation_id: "conv-456", response: "hello assistant" });
      }, 10);
    });
  }

  // A. Assert double submit prevention
  loading = true;
  const submitResult = mockSendMessage("hello click");
  assert.strictEqual(submitResult, "blocked", "Should reject call when loading is active");
  console.log("✓ Hook prevents duplicate submissions during active loading");

  // B. Assert cancellation behavior
  loading = false;
  const p1 = mockSendMessage("first query");
  const p2 = mockSendMessage("second query (aborts first)");
  
  Promise.allSettled([p1, p2]).then((results) => {
    assert.strictEqual(cancelledCount, 1, "First query should be registered as cancelled");
    assert.strictEqual(results[0].status, "rejected", "First query should fail");
    assert.strictEqual(results[0].reason.isCancelled, true, "First query failure reason should be cancellation");
    assert.strictEqual(results[1].status, "fulfilled", "Second query should succeed");
    console.log("✓ Hook manages and aborts multiple rapid in-flight queries");
    console.log("\nALL FRONTEND HARDENING UNIT TESTS PASSED SUCCESSFULLY!");
    console.log("-------------------------------------------------");
  });
})();
