import firebase_admin
from firebase_admin import credentials, firestore, auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.models.user import User 
from app.models.goal import GoalInDB # <-- We need this for type hinting
from typing import List, Dict, Any

# We must re-format the private key from a single-line string
# back to a multi-line string with newlines.
try:
    FIREBASE_PRIVATE_KEY_FORMATTED = settings.FIREBASE_PRIVATE_KEY.replace("\\n", "\n")
except AttributeError:
    raise AttributeError("FIREBASE_PRIVATE_KEY not set or invalid in .env")

# Prepare the credentials dictionary
cred_dict = {
    "type": "service_account",
    "project_id": settings.FIREBASE_PROJECT_ID,
    "private_key_id": "", # Not strictly needed
    "private_key": FIREBASE_PRIVATE_KEY_FORMATTED,
    "client_email": settings.FIREBASE_CLIENT_EMAIL,
    "client_id": "", # Not strictly needed
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.FIREBASE_CLIENT_EMAIL.replace('@', '%40')}"
}

# Initialize Firebase Admin
try:
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully.")
except ValueError as e:
    if "already exists" not in str(e):
        print(f"Error initializing Firebase Admin SDK: {e}")
        print("Please check your FIREBASE_... environment variables.")
except Exception as e:
    if "already exists" not in str(e):
        print(f"An unexpected error occurred: {e}")

# Get the Firestore client
db = firestore.client()
print("Firestore client acquired.")


# Define our bearer token security scheme
oauth2_scheme = HTTPBearer()

# --- Core Authentication Dependency ---

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
) -> User:
    """
    FastAPI dependency that verifies the Firebase ID Token.
    Returns a Pydantic User model.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        decoded_token = auth.verify_id_token(token.credentials)
        # Populate our User model
        return User(
            uid=decoded_token.get("uid"),
            email=decoded_token.get("email"),
            name=decoded_token.get("name"),
            picture=decoded_token.get("picture")
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"An unhandled error occurred during token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token verification",
        )

# --- Google Token CRUD ---

def save_user_google_token(user_id: str, google_refresh_token: str):
    """
    Saves a user's encrypted Google refresh token to Firestore.
    (This is a SYNCHRONOUS function)
    """
    user_ref = db.collection("users").document(user_id)
    try:
        user_ref.set({
            'google_refresh_token': google_refresh_token
        }, merge=True)
        print(f"Successfully saved token for user {user_id}")
    except Exception as e:
        print(f"Error saving token to Firestore for user {user_id}: {e}")
        # We re-raise the exception to be caught by the endpoint
        raise Exception("Could not save user token to database.")

def get_user_google_token(user_id: str) -> str:
    """
    Retrieves a user's encrypted Google refresh token from Firestore.
    (This is a SYNCHRONOUS function)
    """
    user_ref = db.collection("users").document(user_id)
    try:
        doc = user_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data.get('google_refresh_token')
        else:
            print(f"No document found for user {user_id}")
            return None
    except Exception as e:
        print(f"Error getting token from Firestore for user {user_id}: {e}")
        raise Exception("Could not retrieve user token from database.")

# --- (NEW) Goal CRUD Functions ---

def create_user_goal(user_id: str, goal_data: dict) -> str:
    """
    Creates a new goal document for a user in a 'goals' subcollection.
    Returns the new goal's ID.
    (This is a SYNCHRONOUS function)
    """
    try:
        # We store goals in a subcollection under the user
        goals_collection_ref = db.collection("users").document(user_id).collection("goals")
        
        # Add a new document with a generated ID
        update_time, doc_ref = goals_collection_ref.add(goal_data)
        
        print(f"Successfully created goal {doc_ref.id} for user {user_id}")
        return doc_ref.id
    except Exception as e:
        print(f"Error creating goal in Firestore for user {user_id}: {e}")
        raise Exception("Could not create goal in database.")

def get_user_goals(user_id: str) -> List[GoalInDB]:
    """
    Retrieves all goals for a specific user.
    (This is a SYNCHRONOUS function)
    """
    try:
        goals_collection_ref = db.collection("users").document(user_id).collection("goals")
        docs = goals_collection_ref.stream()
        
        goals_list = []
        for doc in docs:
            goal_data = doc.to_dict()
            # Add the document ID and user_id to the data
            goal_data['id'] = doc.id
            goal_data['user_id'] = user_id
            goals_list.append(GoalInDB(**goal_data))
            
        return goals_list
    except Exception as e:
        print(f"Error retrieving goals from Firestore for user {user_id}: {e}")
        raise Exception("Could not retrieve goals from database.")

def get_user_goal(user_id: str, goal_id: str) -> GoalInDB | None:
    """
    Retrieves a single goal for a user by its ID.
    (This is a SYNCHRONOUS function)
    """
    try:
        goal_ref = db.collection("users").document(user_id).collection("goals").document(goal_id)
        doc = goal_ref.get()
        
        if not doc.exists:
            return None
        
        goal_data = doc.to_dict()
        goal_data['id'] = doc.id
        goal_data['user_id'] = user_id
        
        return GoalInDB(**goal_data)
        
    except Exception as e:
        print(f"Error retrieving single goal from Firestore for user {user_id}: {e}")
        raise Exception("Could not retrieve single goal from database.")