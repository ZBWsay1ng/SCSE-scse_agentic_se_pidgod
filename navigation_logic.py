def decide_action(front_blocked, left_blocked, right_blocked, goal_direction=None):
    """Decide the next action based on blocked directions and goal direction."""
    if type(front_blocked) is not bool or type(left_blocked) is not bool or type(right_blocked) is not bool:
        raise ValueError
    if goal_direction is not None:
        if type(goal_direction) is not str or goal_direction not in ('ahead', 'left', 'right'):
            raise ValueError
    if front_blocked and left_blocked and right_blocked:
        return "STOP"
    elif goal_direction == 'ahead' and not front_blocked:
        return "FORWARD"
    elif goal_direction == 'left' and not left_blocked:
        return "LEFT"
    elif goal_direction == 'right' and not right_blocked:
        return "RIGHT"
    else:
        if not front_blocked:
            return "FORWARD"
        elif not left_blocked:
            return "LEFT"
        elif not right_blocked:
            return "RIGHT"
        else:
            return "STOP"
