/*
 * Present OS Frontend Logic
 * This file handles:
 * 1. Firebase Authentication (Auth)
 * 2. API calls to our backend (API)
 * 3. Updating the HTML (UI)
 * This uses the v9 modular Firebase SDK.
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

    // This config is loaded from firebase-config.js
    if (!window.firebaseConfig || !window.firebaseConfig.apiKey) {
        console.error("CRITICAL: firebase-config.js is missing or incorrect.");
        alert("CRITICAL: App configuration is missing. Please check the console.");
        return;
    }
    const app = initializeApp(window.firebaseConfig);
    const auth = getAuth(app);
    const provider = new GoogleAuthProvider();
    
    // Add the Google Calendar scope.
    provider.addScope('https://www.googleapis.com/auth/calendar.events');

    // Our backend API URL
    const BACKEND_URL = "http://localhost:8000/api/v1";

    // --- UI Elements ---
    const loginScreen = document.getElementById("login-screen");
    const dashboardScreen = document.getElementById("dashboard-screen");
    const signInButton = document.getElementById("sign-in-btn");
    const signOutButton = document.getElementById("sign-out-btn");
    const userProfileName = document.getElementById("user-profile-name");
    const userProfilePic = document.getElementById("user-profile-pic");
    const addGoalForm = document.getElementById("add-goal-form");
    const goalsList = document.getElementById("goals-list");
    const goalSelect = document.getElementById("goal-select");
    const scheduleActionForm = document.getElementById("schedule-action-form");
    const personalityButtons = document.querySelectorAll(".personality-btn");
    const scheduleStatus = document.getElementById("schedule-status");
    const permissionStatus = document.getElementById("permission-status");

    let selectedPersonality = "P"; // Default to Producer
    let currentIdToken = null; // We store the token in-memory

    // --- 1. AUTHENTICATION LOGIC ---

    // Listen for Auth State Changes
    onAuthStateChanged(auth, async (user) => {
        if (user) {
            // User is signed in
            console.log("Sign-in successful.");
            try {
                const idToken = await user.getIdToken();
                console.log("ID Token acquired.");
                currentIdToken = idToken; // Save token to app state

                // Show dashboard, hide login
                loginScreen.classList.add("hidden");
                dashboardScreen.classList.remove("hidden");

                // Update UI
                userProfileName.textContent = user.displayName;
                userProfilePic.src = user.photoURL;

                // This is the new, combined flow.
                // 1. Check if we *already* have calendar permission.
                // 2. If not, this function will redirect to get it.
                await checkAndGetCalendarPermission(idToken);
                
                // 3. Load the app's data
                await loadApp(user, idToken);

            } catch (error) {
                console.error("Error during token retrieval or app load:", error);
                // If something fails, sign the user out to be safe
                // signOut(auth); // Commented out to prevent sign-out loops
            }
        } else {
            // User is signed out
            console.log("User signed out.");
            currentIdToken = null;
            loginScreen.classList.remove("hidden");
            dashboardScreen.classList.add("hidden");
        }
    });

    // Sign-In Button
    signInButton.addEventListener("click", () => {
        signInWithPopup(auth, provider)
            .catch((error) => {
                console.error("Google Sign-In Error:", error);
            });
    });

    // Sign-Out Button
    signOutButton.addEventListener("click", () => {
        signOut(auth).catch((error) => {
            console.error("Sign-Out Error:", error);
        });
    });

    // --- 2. PERMISSION & APP LOGIC (THE FIX) ---

    /**
     * Checks if we have calendar permissions. If not, redirects to get them.
     */
    async function checkAndGetCalendarPermission(idToken) {
        if (!idToken) return;
        
        // Check if we're coming *back* from the Google auth redirect
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('success') || urlParams.has('error')) {
            // We just came back. Clear the URL parameters.
            window.history.replaceState({}, document.title, "/");
            return; // We're done, permission flow just finished.
        }

        console.log("Checking calendar permissions...");
        try {
            // --- THIS IS THE CRITICAL FETCH CALL ---
            const response = await fetch(`${BACKEND_URL}/auth/google/login?permission=true`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${idToken}`, 
                    'Content-Type': 'application/json'
                }
            });

            // We will NOT get a redirect. We will get JSON.
            const data = await response.json();

            if (data.status === 'permission_granted') {
                // User already has permission.
                console.log("Calendar permission already granted.");
                permissionStatus.textContent = "Calendar connected.";
                permissionStatus.classList.remove("text-yellow-500");
                permissionStatus.classList.add("text-green-500");

            } else if (data.status === 'permission_needed') {
                // User needs permission. We must redirect the *whole page*.
                console.log("Redirecting to Google for permissions...");
                alert("This app needs access to your Google Calendar. Redirecting you to Google to grant permission.");
                window.location.href = data.auth_url; // This redirects the whole page.

            } else {
                // This will catch other errors
                console.error("Permission check failed (non-redirect):", data);
                permissionStatus.textContent = "Calendar permission needed.";
            }

        } catch (error) {
            // This is a real error
            console.error("Error in checkAndGetCalendarPermission:", error);
            permissionStatus.textContent = "Error connecting to backend.";
        }
    }

    /**
     * Main app loader. Fetches goals and populates the dashboard.
     */
    async function loadApp(user, idToken) {
        if (!idToken) return;

        // Fetch user's goals
        try {
            const response = await fetch(`${BACKEND_URL}/goals/`, {
                headers: { 'Authorization': `Bearer ${idToken}` }
            });
            if (!response.ok) {
                throw new Error('Failed to fetch goals');
            }
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
            // Add to list
            const li = document.createElement("li");
            li.className = "flex justify-between items-center bg-gray-700 p-3 rounded-lg";
            li.innerHTML = `
                <div>
                    <span class="font-semibold text-white">${goal.name}</span>
                    <span class="text-sm text-gray-400 ml-2">(${goal.avatar})</span>
                </div>
                <i data-lucide="target" class="text-indigo-400"></i>
            `;
            goalsList.appendChild(li);

            // Add to dropdown
            const option = document.createElement("option");
            option.value = goal.id;
            option.textContent = `${goal.name} (${goal.avatar})`;
            goalSelect.appendChild(option);
        });

        // Re-initialize icons
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

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
            if (!response.ok) {
                throw new Error('Failed to create goal');
            }
            // Clear form and reload goals
            addGoalForm.reset();
            await loadApp(auth.currentUser, currentIdToken);
        } catch (error) {
            console.error(error);
        }
    });

    // --- 4. ACTION SCHEDULING ---

    personalityButtons.forEach(button => {
        button.addEventListener("click", () => {
            // Remove active state from all buttons
            personalityButtons.forEach(btn => btn.classList.remove("bg-indigo-600"));
            // Add active state to clicked button
            button.classList.add("bg-indigo-600");
            // Set the selected personality
            selectedPersonality = button.dataset.personality;
        });
    });

    scheduleActionForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const taskPrompt = document.getElementById("task-prompt").value;
        const goalId = document.getElementById("goal-select").value;

        if (!taskPrompt || !goalId || !selectedPersonality || !currentIdToken) {
            scheduleStatus.textContent = "Please fill out all fields.";
            scheduleStatus.className = "text-yellow-500 mt-2";
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

        scheduleStatus.textContent = "Scheduling...";
        scheduleStatus.className = "text-gray-400 mt-2";

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
            scheduleStatus.innerHTML = `
                Success! Event created. 
                <a href="${result.event_link}" target="_blank" class="text-indigo-400 underline">
                    View on Calendar
                </a>
            `;
            scheduleStatus.className = "text-green-500 mt-2";
            scheduleActionForm.reset();

        } catch (error) {
            console.error(error);
            scheduleStatus.textContent = `Error: ${error.message}`;
            scheduleStatus.className = "text-red-500 mt-2";
        }
    });

    // --- 5. INITIALIZE LUCIDE ICONS (for login screen) ---
    if (window.lucide) {
        window.lucide.createIcons();
    }
});