/*
 * Present OS Frontend Logic
 * This file handles:
 * 1. Firebase Authentication (Auth)
 * 2. API calls to our backend (API)
 * 3. Updating the HTML (UI)
 */
document.addEventListener("DOMContentLoaded", () => {
    // --- 0. CONFIGURATION & IMPORTS ---
    const { initializeApp } = window.firebase.app;
    const { 
        getAuth, 
        onAuthStateChanged, 
        GoogleAuthProvider, 
        signInWithPopup, 
        signOut 
    } = window.firebase.auth;

    if (!window.firebaseConfig || !window.firebaseConfig.apiKey) {
        console.error("CRITICAL: firebase-config.js is missing or incorrect.");
        // Use the status helper instead of alert()
        showStatus("CRITICAL: App configuration is missing. Check console.", "error");
        return;
    }
    const app = initializeApp(window.firebaseConfig);
    const auth = getAuth(app);
    const provider = new GoogleAuthProvider();
    provider.addScope('https://www.googleapis.com/auth/calendar.events');

    const BACKEND_URL = "http://localhost:8000/api/v1";

    // --- UI Elements ---
    const loginScreen = document.getElementById("login-screen");
    const dashboardScreen = document.getElementById("dashboard-screen");
    const signInButton = document.getElementById("sign-in-btn");
    const signOutButton = document.getElementById("sign-out-btn");
    const userProfileName = document.getElementById("user-profile-name");
    const userProfilePic = document.getElementById("user-profile-pic");

    // UPDATED: Goal elements
    const addGoalForm = document.getElementById("add-goal-form");
    const goalsList = document.getElementById("goals-list");
    const showAddGoalButton = document.getElementById("show-add-goal-btn");
    const cancelAddGoalButton = document.getElementById("cancel-add-goal-btn");
    
    const goalSelect = document.getElementById("goal-select");
    const scheduleActionForm = document.getElementById("schedule-action-form");
    const personalityButtons = document.querySelectorAll(".personality-btn");
    const scheduleStatus = document.getElementById("schedule-status");
    const permissionStatus = document.getElementById("permission-status");
    const tabButtons = document.querySelectorAll(".tab-switcher");
    const actionPanels = document.querySelectorAll(".action-panel");

    // NEW: Logout Modal Elements
    const logoutModal = document.getElementById("logout-modal");
    const cancelLogoutButton = document.getElementById("cancel-logout-btn");
    const confirmLogoutButton = document.getElementById("confirm-logout-btn");

    let selectedPersonality = "P"; 
    let currentIdToken = null; 

    // --- 1. AUTHENTICATION LOGIC ---

    onAuthStateChanged(auth, async (user) => {
        if (user) {
            console.log("Sign-in successful.");
            try {
                currentIdToken = await user.getIdToken();
                console.log("ID Token acquired.");

                loginScreen.classList.add("hidden");
                dashboardScreen.classList.remove("hidden");

                userProfileName.textContent = user.displayName;
                userProfilePic.src = user.photoURL;

                await checkAndGetCalendarPermission(currentIdToken);
                await loadApp(user, currentIdToken);

                // Initialize Feather Icons *after* dashboard is visible
                feather.replace();

            } catch (error) {
                console.error("Error during token retrieval or app load:", error);
            }
        } else {
            console.log("User signed out.");
            currentIdToken = null;
            loginScreen.classList.remove("hidden");
            dashboardScreen.classList.add("hidden");
            // Hide modal if it was open
            logoutModal.classList.add("hidden");
        }
    });

    signInButton.addEventListener("click", () => {
        signInWithPopup(auth, provider)
            .catch((error) => console.error("Google Sign-In Error:", error));
    });

    // NEW: Sign-Out Button shows modal
    signOutButton.addEventListener("click", () => {
        logoutModal.classList.remove("hidden");
    });

    // NEW: Logout Modal logic
    cancelLogoutButton.addEventListener("click", () => {
        logoutModal.classList.add("hidden");
    });

    confirmLogoutButton.addEventListener("click", () => {
        signOut(auth).catch((error) => console.error("Sign-Out Error:", error));
        // Modal will hide automatically because of onAuthStateChanged
    });

    // --- 2. PERMISSION & APP LOGIC ---

    async function checkAndGetCalendarPermission(idToken) {
        if (!idToken) return;
        
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('success') || urlParams.has('error')) {
            window.history.replaceState({}, document.title, "/");
            if(urlParams.has('success')) {
                permissionStatus.textContent = "Calendar connected successfully!";
                permissionStatus.className = "text-green-500 text-sm";
            } else {
                permissionStatus.textContent = "Failed to connect calendar.";
                permissionStatus.className = "text-red-500 text-sm";
            }
            return;
        }

        console.log("Checking calendar permissions...");
        try {
            const response = await fetch(`${BACKEND_URL}/auth/google/login?permission=true`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${idToken}`, 
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();

            if (data.status === 'permission_granted') {
                console.log("Calendar permission already granted.");
                permissionStatus.textContent = "Calendar connected.";
                permissionStatus.classList.remove("text-yellow-500");
                permissionStatus.classList.add("text-green-500");
            } else if (data.status === 'permission_needed') {
                console.log("Redirecting to Google for permissions...");
                showStatus("This app needs access to your Google Calendar. Redirecting...", "info");
                setTimeout(() => {
                    window.location.href = data.auth_url;
                }, 2000); // 2-second delay
            } else {
                console.error("Permission check failed:", data);
                permissionStatus.textContent = "Calendar permission needed.";
            }
        } catch (error) {
            console.error("Error in checkAndGetCalendarPermission:", error);
            permissionStatus.textContent = "Error connecting to backend.";
        }
    }

    async function loadApp(user, idToken) {
        if (!idToken) return;
        try {
            const response = await fetch(`${BACKEND_URL}/goals/`, {
                headers: { 'Authorization': `Bearer ${idToken}` }
            });
            if (!response.ok) throw new Error('Failed to fetch goals');
            const goals = await response.json();
            renderGoals(goals);
        } catch (error) {
            console.error(error);
        }
    }

    // --- 3. GOAL MANAGEMENT ---

    function renderGoals(goals) {
        goalsList.innerHTML = "";
        goalSelect.innerHTML = '<option value="">Select a goal</option>';
        
        if (goals.length === 0) {
            goalsList.innerHTML = '<p class="text-gray-400">No goals created yet. Add one!</p>';
            return;
        }

        goals.forEach(goal => {
            const li = document.createElement("li");
            li.className = "flex justify-between items-center bg-gray-700 p-3 rounded-lg";
            li.innerHTML = `
                <div>
                    <span class="font-semibold text-white">${goal.name}</span>
                    <span class="text-sm text-gray-400 ml-2">(${goal.avatar})</span>
                </div>
                <i data-feather="target" class="text-indigo-400"></i>
            `;
            goalsList.appendChild(li);

            const option = document.createElement("option");
            option.value = goal.id;
            option.textContent = `${goal.name} (${goal.avatar})`;
            goalSelect.appendChild(option);
        });

        // Re-initialize icons
        feather.replace();
    }

    // UPDATED: Show/Hide Goal Form
    showAddGoalButton.addEventListener("click", () => {
        addGoalForm.classList.remove("hidden");
        goalsList.classList.add("hidden");
        showAddGoalButton.classList.add("hidden");
    });

    cancelAddGoalButton.addEventListener("click", () => {
        addGoalForm.classList.add("hidden");
        goalsList.classList.remove("hidden");
        showAddGoalButton.classList.remove("hidden");
        addGoalForm.reset();
    });

    addGoalForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const goalName = document.getElementById("goal-name").value;
        const goalAvatar = document.getElementById("goal-avatar").value;
        if (!goalName || !goalAvatar || !currentIdToken) return;

        try {
            const response = await fetch(`${BACKEND_URL}/goals/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${currentIdToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: goalName,
                    description: "Created from app",
                    avatar: goalAvatar
                })
            });
            if (!response.ok) throw new Error('Failed to create goal');
            
            // UPDATED: Hide form and show list on success
            addGoalForm.reset();
            addGoalForm.classList.add("hidden");
            goalsList.classList.remove("hidden");
            showAddGoalButton.classList.remove("hidden");
            
            await loadApp(auth.currentUser, currentIdToken); // Reload goals
        } catch (error) {
            console.error(error);
        }
    });

    // --- 4. ACTION SCHEDULING ---

    personalityButtons.forEach(button => {
        button.addEventListener("click", () => {
            personalityButtons.forEach(btn => {
                btn.classList.remove("bg-indigo-600", "text-white");
                if (!btn.classList.contains("text-gray-300")) {
                    btn.classList.add("text-gray-300", "hover:bg-gray-700");
                }
            });
            button.classList.add("bg-indigo-600", "text-white");
            button.classList.remove("text-gray-300", "hover:bg-gray-700");
            selectedPersonality = button.dataset.personality;
        });
    });

    scheduleActionForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const taskPrompt = document.getElementById("task-prompt").value;
        const goalId = document.getElementById("goal-select").value;

        if (!taskPrompt || !goalId || !selectedPersonality || !currentIdToken) {
            showStatus("Please fill out all fields.", "warning");
            return;
        }

        const payload = {
            task_type: "schedule_task",
            payload: {
                task_prompt: taskPrompt,
                goal_id: goalId,
                personality: selectedPersonality
            }
        };

        showStatus("Scheduling...", "info");

        try {
            const response = await fetch(`${BACKEND_URL}/actions/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${currentIdToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to schedule task');
            }

            const result = await response.json();
            showStatus(
                `Success! Event created. <a href="${result.event_link}" target="_blank" class="text-indigo-400 underline">View on Calendar</a>`,
                "success"
            );
            scheduleActionForm.reset();

        } catch (error) {
            console.error(error);
            showStatus(`Error: ${error.message}`, "error");
        }
    });

    // --- 5. TAB SWITCHING LOGIC ---
    tabButtons.forEach(button => {
        button.addEventListener("click", () => {
            const targetTab = button.dataset.tab; 

            // Update tab button active states
            tabButtons.forEach(btn => {
                btn.classList.remove("active", "bg-indigo-600", "text-white", "shadow-lg");
                btn.classList.add("text-gray-400", "hover:bg-gray-700", "hover:text-white");
            });
            button.classList.add("active", "bg-indigo-600", "text-white", "shadow-lg");
            button.classList.remove("text-gray-400", "hover:bg-gray-700", "hover:text-white");

            // Show/hide action panels
            actionPanels.forEach(panel => {
                if (panel.id === `${targetTab}-action-panel`) {
                    panel.classList.remove("hidden");
                } else {
                    panel.classList.add("hidden");
                }
            });
            
            // Re-render icons
            feather.replace();
        });
    });

    // --- 6. UTILITY FUNCTIONS ---

    function showStatus(message, type = "info") {
        scheduleStatus.innerHTML = message;
        switch (type) {
            case "success":
                scheduleStatus.className = "text-green-500 mt-2 text-sm";
                break;
            case "warning":
                scheduleStatus.className = "text-yellow-500 mt-2 text-sm";
                break;
            case "error":
                scheduleStatus.className = "text-red-500 mt-2 text-sm";
                break;
            default:
                scheduleStatus.className = "text-gray-400 mt-2 text-sm";
        }
    }

    // --- 7. INITIALIZE FEATHER ICONS (for login screen) ---
    feather.replace();
});