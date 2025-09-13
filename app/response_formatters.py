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
        response += f"\n<b>{workout['id']}. {workout['name']}</b>\n"
        response += f"<blockquote>{workout['description']}</blockquote>\n"
        response += f"   Теги: {tags}\n"
        response += f"   Выполнений: {workout.get('reps', 0)}\n"
    
    return response


def format_weight_period_response(period):
    """Format weight period response message"""
    return f"📊 График веса за период: {period}"