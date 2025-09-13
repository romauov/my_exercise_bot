import json
import random
from datetime import datetime


def get_random_workout_by_difficulty(difficulty):
    """Get a random workout by difficulty level"""
    try:
        with open('workout_cards.json', 'r', encoding='utf-8') as f:
            workouts = json.load(f)
        
        filtered_workouts = [w for w in workouts if difficulty in w.get("tags", [])]
        
        if filtered_workouts:
            return random.choice(filtered_workouts)
        return None
    except FileNotFoundError:
        return None


def update_workout_history(workout_id):
    """Update workout history and increment reps counter"""
    try:
        # Read current workouts
        with open('workout_cards.json', 'r', encoding='utf-8') as f:
            workouts = json.load(f)
        
        # Find the workout and update its history and reps
        for workout in workouts:
            if workout['id'] == workout_id:
                # Add current timestamp to history
                workout['history'].append(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
                # Increment reps counter
                current_reps = workout.get('reps', 0)
                workout['reps'] = current_reps + 1
                print(f"Updated workout {workout_id}: reps from {current_reps} to {workout['reps']}")
                break
        
        # Save updated workouts back to file
        with open('workout_cards.json', 'w', encoding='utf-8') as f:
            json.dump(workouts, f, ensure_ascii=False, indent=2)
            
        return True
    except Exception as e:
        print(f"Error updating workout history: {e}")
        return False


def add_workout_to_file(name, description, tags):
    """Add a new workout to the workout cards file with sequential ID"""
    try:
        # Read current workouts
        try:
            with open('workout_cards.json', 'r', encoding='utf-8') as f:
                workouts = json.load(f)
        except FileNotFoundError:
            workouts = []
        
        # Generate new ID (sequential)
        new_id = str(len(workouts) + 1)
        
        # Create new workout object
        new_workout = {
            "id": new_id,
            "name": name,
            "description": description,
            "tags": tags,
            "history": [],
            "reps": 0
        }
        
        # Add to workouts list
        workouts.append(new_workout)
        
        # Save updated workouts back to file
        with open('workout_cards.json', 'w', encoding='utf-8') as f:
            json.dump(workouts, f, ensure_ascii=False, indent=2)
            
        return new_workout
    except Exception as e:
        print(f"Error adding workout: {e}")
        return None


def remove_workout_from_file(workout_id):
    """Remove a workout from the workout cards file and reset IDs"""
    try:
        # Read current workouts
        with open('workout_cards.json', 'r', encoding='utf-8') as f:
            workouts = json.load(f)
        
        # Find and remove workout
        removed_workout = None
        for i, workout in enumerate(workouts):
            if workout['id'] == workout_id:
                removed_workout = workouts.pop(i)
                break
        
        # Reset IDs to be sequential
        for i, workout in enumerate(workouts):
            workout['id'] = str(i + 1)
        
        # Save updated workouts back to file
        with open('workout_cards.json', 'w', encoding='utf-8') as f:
            json.dump(workouts, f, ensure_ascii=False, indent=2)
            
        return removed_workout
    except Exception as e:
        print(f"Error removing workout: {e}")
        return None


def get_all_workouts():
    """Get all workouts from the workout cards file"""
    try:
        with open('workout_cards.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []