import numpy as np
import pandas as pd
import redis
import cv2
import re
import insightface
from insightface.app import FaceAnalysis
from sklearn.metrics import pairwise
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import os

# Connect to Redis Client
import streamlit as st

# Redis connection configuration from Streamlit secrets
hostname = st.secrets["REDIS_HOST"]  # If using Streamlit
portnumber = st.secrets["REDIS_PORT"]
password = st.secrets["REDIS_PASSWORD"]

# Initialize Redis connection
r = redis.StrictRedis(host=hostname, port=portnumber, password=password)

def retrive_data(name):
    """
    Retrieve facial recognition data from Redis database and format it into a DataFrame.
    
    Args:
        name (str): The Redis hash key to retrieve data from (e.g., 'staff:register')
        
    Returns:
        pd.DataFrame: A DataFrame containing staff information with columns:
            - ID_Name_Role: Original composite key from Redis
            - File No. Name: Formatted file number and name
            - Role: Staff role/position
            - Facial_features: Extracted facial embeddings
            - Zone: Geographic zone (defaults to 'Lagos Zone 2')
    """
    retrive_dict = r.hgetall(name)
    retrive_series = pd.Series(retrive_dict)
    retrive_series = retrive_series.apply(lambda x: np.frombuffer(x, dtype=np.float32))
    index = retrive_series.index
    index = list(map(lambda x: x.decode(), index))
    retrive_series.index = index
    retrive_df = retrive_series.to_frame().reset_index()
    retrive_df.columns = ['ID_Name_Role', 'Facial_features']
    
    # Initialize default values
    retrive_df['File No. Name'] = ''
    retrive_df['Role'] = ''
    retrive_df['Zone'] = 'Lagos Zone 2'  # Default zone
    
    # Process each record safely
    for i, row in retrive_df.iterrows():
        try:
            parts = row['ID_Name_Role'].split('@')
            
            # Extract file no and name (first part before @)
            file_name_role = parts[0]
            file_no, name = file_name_role.split('.', 1)
            
            # Extract role (second part)
            role = parts[1] if len(parts) > 1 else ''
            
            # Extract zone if available (third part in new format)
            zone = parts[2] if len(parts) > 2 else 'Lagos Zone 2'
            
            # Update the row
            retrive_df.at[i, 'File No. Name'] = f"{file_no}.{name}"
            retrive_df.at[i, 'Role'] = role
            retrive_df.at[i, 'Zone'] = zone
            
        except Exception as e:
            print(f"Error processing record {row['ID_Name_Role']}: {str(e)}")
            continue
    
    return retrive_df[['ID_Name_Role', 'File No. Name', 'Role', 'Facial_features', 'Zone']]

def load_logs(name, end=-1):
    """
    Load logs from Redis list.
    
    Args:
        name (str): Redis list key (e.g., 'attendance:logs')
        end (int): Index of last item to retrieve (default -1 for all items)
        
    Returns:
        list: List of log entries (bytes objects that need decoding)
    """
    logs_list = r.lrange(name, start=0, end=end)
    return logs_list

# Configure face analysis model
faceapp = FaceAnalysis(name='buffalo_sc',
                     root='insightface_model',
                     providers=['CPUExecutionProvider'])
faceapp.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.5)

def ml_search_algorithm(dataframe, feature_column, test_vector, name_role=['File No. Name', 'Role'], thresh=0.5):
    """
    Perform facial recognition search using cosine similarity.
    
    Args:
        dataframe (pd.DataFrame): DataFrame containing staff facial features
        feature_column (str): Name of column containing facial embeddings
        test_vector (np.array): Facial embedding to compare against
        name_role (list): Column names for name and role in dataframe
        thresh (float): Similarity threshold for positive match (0-1)
        
    Returns:
        tuple: (matched_name, matched_role) or ('Unknown', 'Unknown') if no match
    """
    dataframe = dataframe.copy()
    X_list = dataframe[feature_column].tolist()
    X_cleaned = []
    indices = []

    # Clean and validate input vectors
    for i, item in enumerate(X_list):
        if isinstance(item, (list, np.ndarray)) and len(item) > 0:
            item_arr = np.array(item)
            if item_arr.shape == test_vector.shape:
                X_cleaned.append(item_arr)
                indices.append(i)

    if len(X_cleaned) == 0:
        return 'Unknown', 'Unknown'

    dataframe = dataframe.iloc[indices].reset_index(drop=True)
    x = np.array(X_cleaned)
    similar = cosine_similarity(x, test_vector.reshape(1, -1))
    similar_arr = similar.flatten()
    dataframe['cosine'] = similar_arr
    data_filter = dataframe[dataframe['cosine'] >= thresh]

    if not data_filter.empty:
        best_match = data_filter.sort_values(by='cosine', ascending=False).iloc[0]
        person_name, person_role = best_match[name_role[0]], best_match[name_role[1]]
    else:
        person_name, person_role = 'Unknown', 'Unknown'

    return person_name, person_role

class RealTimePrediction:
    """
    Class for handling real-time facial recognition predictions and attendance logging.
    
    Attributes:
        logs (dict): Temporary storage for recognition results before saving to Redis
    """
    
    def __init__(self):
        """Initialize with empty logs dictionary"""
        self.logs = dict(name=[], role=[], current_time=[])
    
    def reset_dict(self):
        """Reset the logs dictionary to empty state"""
        self.logs = dict(name=[], role=[], current_time=[])

    def check_last_action(self, name, current_action):
        """
        Check if the current action is valid based on previous logs.
        
        Args:
            name (str): Staff name to check
            current_action (str): Current action ('Clock_In' or 'Clock_Out')
            
        Returns:
            bool: True if action is valid, False if it violates sequence rules
        """
        if name == 'Unknown':
            return True
        
        logs = load_logs('attendance:logs', end=10)
        last_action = None
        last_date = None
        
        for log in logs:
            if isinstance(log, bytes):
                log = log.decode('utf-8')
            
            parts = log.split('@')
            if len(parts) == 4:
                log_name, _, log_timestamp, log_action = parts
                if log_name == name:
                    try:
                        log_datetime = datetime.strptime(log_timestamp.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        log_date = log_datetime.date()
                        
                        if last_date is None or log_datetime > last_date:
                            last_action = log_action
                            last_date = log_datetime
                    except:
                        continue
        
        if last_action is None:
            return True
        
        current_date = datetime.now().date()
        same_day = (last_date.date() == current_date) if last_date else False
        
        if not same_day:
            return True
        
        if last_action == 'Clock_In' and current_action == 'Clock_Out':
            return True
        elif last_action == 'Clock_Out' and current_action == 'Clock_In':
            return True
        elif last_action == current_action:
            return False
        
        return True

    def saveLogs_redis(self, Clock_In_Out):
        """
        Save recognition logs to Redis after validation.
        
        Args:
            Clock_In_Out (str): Type of action ('Clock_In' or 'Clock_Out')
        """
        dataframe = pd.DataFrame(self.logs)
        dataframe.drop_duplicates('name', inplace=True)
        name_list = dataframe['name'].tolist()
        role_list = dataframe['role'].tolist()
        current_time_list = dataframe['current_time'].tolist()
        encoded_data = []

        for name, role, current_time in zip(name_list, role_list, current_time_list):
            if name != 'Unknown':
                if self.check_last_action(name, Clock_In_Out):
                    concat_string = f"{name}@{role}@{current_time}@{Clock_In_Out}"
                    encoded_data.append(concat_string)
                else:
                    print(f"Action blocked: {name} attempted {Clock_In_Out} after previous action")

        if len(encoded_data) > 0:
            r.lpush('attendance:logs', *encoded_data)

        self.reset_dict()

    def face_prediction(self, test_image, dataframe, feature_column, name_role=['File No. Name', 'Role'], thresh=0.5):
        """
        Perform face detection and recognition on an input image.
        
        Args:
            test_image (np.array): Input image frame
            dataframe (pd.DataFrame): Staff database with facial features
            feature_column (str): Column name containing facial embeddings
            name_role (list): Column names for name and role
            thresh (float): Similarity threshold for recognition
            
        Returns:
            np.array: Annotated image with detection boxes and recognition results
        """
        current_time = str(datetime.now())
        results = faceapp.get(test_image)
        test_copy = test_image.copy()
        
        for res in results:
            x1, y1, x2, y2 = res['bbox'].astype(int)
            embeddings = res['embedding']
            person_name, person_role = ml_search_algorithm(dataframe, 
                                                          feature_column,
                                                          test_vector=embeddings,
                                                          name_role=name_role,
                                                          thresh=thresh)
            
            if person_name == 'Unknown':
                color = (0, 0, 255)  # Red for unknown
            else:
                color = (0, 255, 0)  # Green for known
            
            cv2.rectangle(test_copy, (x1, y1), (x2, y2), color)
            text_gen = person_name
            cv2.putText(test_copy, text_gen, (x1, y1), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)
            cv2.putText(test_copy, current_time, (x1, y2+10), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)

            self.logs['name'].append(person_name)
            self.logs['role'].append(person_role)
            self.logs['current_time'].append(current_time)
        
        return test_copy

class RegistrationForm:
    """
    Class for handling new staff registration and facial feature collection.
    
    Attributes:
        sample (int): Counter for collected face samples
    """
    
    def __init__(self):
        """Initialize with sample counter at 0"""
        self.sample = 0

    def reset(self):
        """Reset the sample counter to 0"""
        self.sample = 0

    def get_embedding(self, frame):
        """
        Detect faces in frame and collect embeddings.
        
        Args:
            frame (np.array): Input image frame
            
        Returns:
            tuple: (annotated_frame, embeddings) where:
                - annotated_frame: Input frame with detection boxes drawn
                - embeddings: Facial embeddings if face detected, else None
        """
        results = faceapp.get(frame)
        embeddings = None
        
        if results:
            for res in results:
                self.sample += 1
                x1, y1, x2, y2 = res['bbox'].astype(int)
                
                # Clamp coordinates to frame dimensions
                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w - 1, x2), min(h - 1, y2)
                
                # Draw blue box (BGR: (255, 0, 0))
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                # Draw text above the box
                text = f"samples = {self.sample}"
                cv2.putText(frame, text, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 2)
                
                embeddings = res['embedding']
        
        return frame, embeddings
    
    def save_data_in_redis_db(self, file_number, first_name, last_name, role, zone='Lagos Zone 2'):
        """
        Save collected facial features to Redis database.
        
        Args:
            file_number (str): Staff file number/ID
            first_name (str): Staff first name
            last_name (str): Staff last name
            role (str): Staff position/role
            zone (str): Geographic zone (default 'Lagos Zone 2')
            
        Returns:
            str/bool: True if successful, error message string if failed
        """
        if file_number is not None:
            if first_name.strip() != '':
                key = f"{file_number}.{first_name}.{last_name}@{role}@{zone}"
            else:
                return 'false first_name'
        else:
            return 'false file number'
        
        if 'face_embedding.txt' not in os.listdir():
            return 'No face_embedding.txt'

        # load face_embedding.txt and convert into array
        x_array = np.loadtxt('face_embedding.txt', dtype=np.float32)

        received_samples = int(x_array.size/512)
        x_array = x_array.reshape(received_samples,512)
        x_array = np.asarray(x_array)

        # calc. the mean embeddings
        x_mean = x_array.mean(axis=0)
        x_mean = x_mean.astype(np.float32)
        x_mean_bytes = x_mean.tobytes()

        # save into redis database
        r.hset(name='staff:register', key=key, value=x_mean_bytes)

        os.remove('face_embedding.txt')
        self.reset()
        
        return True

class StaffMovement:
    """
    Class for handling staff movement tracking with facial verification.
    
    Attributes:
        recognizer (RealTimePrediction): Instance for face recognition
        staff_df (pd.DataFrame): Staff database with facial features
        sample (int): Counter for collected face samples
    """
    
    def __init__(self):
        """Initialize with RealTimePrediction instance and loaded staff data"""
        self.recognizer = RealTimePrediction()
        self.staff_df = retrive_data(name='staff:register')
        self.sample = 0
    
    def reset(self):
        """Reset sample counter and clean up temporary files"""
        self.sample = 0
        if os.path.exists('movement_embedding.txt'):
            os.remove('movement_embedding.txt')

    def get_embedding(self, frame):
        """
        Capture face embeddings for movement verification.
        
        Args:
            frame (np.array): Input image frame
            
        Returns:
            np.array: Annotated frame with detection boxes drawn
        """
        results = faceapp.get(frame)
        reg_img = frame.copy()
        embeddings = None
        
        if results:
            for res in results:
                self.sample += 1
                x1, y1, x2, y2 = res['bbox'].astype(int)
                
                # Clamp coordinates to frame dimensions
                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w - 1, x2), min(h - 1, y2)
                
                # Draw blue box (BGR: (255, 0, 0))
                cv2.rectangle(reg_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                # Draw text above the box
                text = f"samples = {self.sample}"
                cv2.putText(reg_img, text, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 2)
                
                embeddings = res['embedding']
        
        # Save embedding to file if exists
        if embeddings is not None:
            with open('movement_embedding.txt', mode='ab') as f:
                np.savetxt(f, embeddings)
        
        return reg_img

    def save_movement_data(self, movement_type, purpose, location, note):
        """
        Save verified movement data to Redis.
        
        Args:
            movement_type (str): Type of movement (e.g., 'Field_Visit')
            purpose (str): Purpose of movement
            location (str): Destination location
            note (str): Additional notes
            
        Returns:
            str/bool: True if successful, error message if verification fails
        """
        # Check if face data exists
        if not os.path.exists('movement_embedding.txt'):
            return 'No face embedding found'
        
        # Load and process embeddings
        x_array = np.loadtxt('movement_embedding.txt', dtype=np.float32)
        x_array = x_array.reshape(-1, 512)
        x_mean = x_array.mean(axis=0)
        
        # Verify staff
        person_name, person_role = ml_search_algorithm(
            self.staff_df,
            'Facial_features',
            test_vector=x_mean,
            thresh=0.5
        )
        
        if person_name == 'Unknown':
            self.reset()
            return 'Verification failed - Unknown staff'
        
        # Prepare data for Redis
        current_time = str(datetime.now())
        movement_data = f"{person_name}@{person_role}@{current_time}@{movement_type}@{purpose}@{location}@{note}"
        
        # Save to Redis
        r.lpush('staff:movement:logs', movement_data)
        self.reset()
        
        return True

class StaffDutyReport:
    """
    Class for handling duty report submission with facial verification.
    
    Attributes:
        recognizer (RealTimePrediction): Instance for face recognition
        staff_df (pd.DataFrame): Staff database with facial features
        sample (int): Counter for collected face samples
    """
    
    def __init__(self):
        """Initialize with RealTimePrediction instance and loaded staff data"""
        self.recognizer = RealTimePrediction()
        self.staff_df = retrive_data(name='staff:register')
        self.sample = 0
    
    def reset(self):
        """Reset sample counter and clean up temporary files"""
        self.sample = 0
        if os.path.exists('duty_report_embedding.txt'):
            os.remove('duty_report_embedding.txt')

    def get_embedding(self, frame):
        """
        Capture face embeddings for report verification.
        
        Args:
            frame (np.array): Input image frame
            
        Returns:
            np.array: Annotated frame with detection boxes drawn
        """
        results = faceapp.get(frame)
        reg_img = frame.copy()
        embeddings = None
        
        if results:
            for res in results:
                self.sample += 1
                x1, y1, x2, y2 = res['bbox'].astype(int)
                
                # Clamp coordinates to frame dimensions
                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w - 1, x2), min(h - 1, y2)
                
                # Draw blue box
                cv2.rectangle(reg_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                # Draw text above the box
                text = f"samples = {self.sample}"
                cv2.putText(reg_img, text, (x1, y1 - 10), 
                          cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 2)
                
                embeddings = res['embedding']
        
        # Save embedding to file if exists
        if embeddings is not None:
            with open('duty_report_embedding.txt', mode='ab') as f:
                np.savetxt(f, embeddings)
        
        return reg_img

    def save_duty_report(self, report_data):
        """
        Save the verified duty report to Redis.
        
        Args:
            report_data (dict): Dictionary containing report details
            
        Returns:
            str/bool: True if successful, error message if verification fails
        """
        # Verify signer's identity
        if not os.path.exists('duty_report_embedding.txt'):
            return 'No face verification found'
        
        # Load and process embeddings
        x_array = np.loadtxt('duty_report_embedding.txt', dtype=np.float32)
        x_array = x_array.reshape(-1, 512)
        x_mean = x_array.mean(axis=0)
        
        # Verify staff
        signer_name, signer_role = ml_search_algorithm(
            self.staff_df,
            'Facial_features',
            test_vector=x_mean,
            thresh=0.5
        )
        
        if signer_name == 'Unknown':
            self.reset()
            return 'Verification failed - Unknown staff'
        
        # Prepare data for Redis
        current_time = str(datetime.now())
        report_data['signer'] = f"{signer_name}@{signer_role}"
        report_data['timestamp'] = current_time
        
        # Save to Redis
        r.hset(f'duty_report:{current_time}', mapping=report_data)
        self.reset()
        
        return True

def migrate_redis_data():
    """
    Migration function to add zone information to existing Redis records.
    Updates old format (name@role) to new format (name@role@zone).
    
    Returns:
        str: Migration completion message
    """
    # Retrieve all existing data
    old_data = r.hgetall('staff:register')
    
    for key, value in old_data.items():
        key_str = key.decode('utf-8')
        # Check if the key already has zone information
        if key_str.count('@') == 1:  # Old format without zone
            # Add default zone
            new_key = f"{key_str}@Lagos Zone 2"
            # Update Redis with new key
            r.hset('staff:register', new_key, value)
            # Remove old key
            r.hdel('staff:register', key)
    
    return "Migration completed successfully"