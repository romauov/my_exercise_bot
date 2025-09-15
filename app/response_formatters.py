def format_workout_response(workout, difficulty):
    """Format workout response message"""
    response = f"<b>Тренировка:</b> {workout['name']}\n\n"
    response += f"<b>Описание:</b>\n<blockquote>{workout['description']}</blockquote>\n\n"
    response += f"<b>Сложность:</b> {difficulty}\n"
    response += f"<b>Количество выполнений:</b> {workout.get('reps', 0)}"
    return response


def format_workout_list_response(workouts):
    """Format workout list response message"""
    if not workouts:
        return "😔 Список тренировок пуст."
    
    response = "<b>📋 Список всех тренировок:</b>\n"
    
    for workout in workouts:
        tags = ', '.join(workout.get('tags', []))
        workout_info = f"\n<b>{workout['id']}. {workout['name']}</b>\n"
        workout_info += f"<blockquote>{workout['description']}</blockquote>\n"
        workout_info += f"   Теги: {tags}\n"
        workout_info += f"   Выполнений: {workout.get('reps', 0)}\n"
        
        # Check if adding this workout would exceed the Telegram message limit
        if len(response + workout_info) > 4000:  # Using 4000 to leave some buffer
            # Return what we have so far and start a new message
            response += "\n<i>(Список продолжается в следующем сообщении...)</i>"
            break
        else:
            response += workout_info
    
    return response


def format_workout_list_response_parts(workouts):
    """Format workout list response message, splitting into multiple parts if needed"""
    if not workouts:
        return ["😔 Список тренировок пуст."]
    
    parts = []
    current_part = "<b>📋 Список всех тренировок:</b>\n"
    remaining_workouts = workouts.copy()
    
    while remaining_workouts:
        workout = remaining_workouts.pop(0)
        tags = ', '.join(workout.get('tags', []))
        workout_info = f"\n<b>{workout['id']}. {workout['name']}</b>\n"
        workout_info += f"<blockquote>{workout['description']}</blockquote>\n"
        workout_info += f"   Теги: {tags}\n"
        workout_info += f"   Выполнений: {workout.get('reps', 0)}\n"
        
        # Check if adding this workout would exceed the Telegram message limit
        if len(current_part + workout_info) > 4000:  # Using 4000 to leave some buffer
            # Add continuation message and save current part
            current_part += "\n<i>(Продолжение следует...)</i>"
            parts.append(current_part)
            
            # Start new part with header and this workout
            current_part = "<b>📋 Список всех тренировок (продолжение):</b>\n" + workout_info
        else:
            current_part += workout_info
    
    # Add the last part
    parts.append(current_part)
    
    return parts


def format_weight_period_response(period):
    """Format weight period response message"""
    return f"📊 График веса за период: {period}"