
class ContinueLoop(BaseException): pass

def inputwhile(prompt: str, callback: callable, *args, **kwargs):
    """
    Continuously prompts the user for input until a valid value is provided.
    
    Args:
        prompt (str): The prompt to display to the user.
        callback (callable): A callback function that will be called with the user's input.
    
    Returns:
        None
    """
    while True:
        try:
            callback(input(prompt), *args, **kwargs)
        except ContinueLoop as e:
            print(e)
            continue
        else:
            break

def input_int(prompt: str, min: int, max: int) -> int:
    """
    Prompts the user for an integer value within a specified range.
    
    Args:
        prompt (str): The prompt to display to the user.
        min (int): The minimum value that the user can input.
        max (int): The maximum value that the user can input.
    
    Returns:
        int: The integer value provided by the user.
    """
    while True:
        try:
            value = int(input(prompt))
        except ValueError:
            print("Please enter a valid integer.")
            continue
        if value < min or value > max:
            print(f"Please enter an integer between {min} and {max}.")
            continue
        return value
    

def inputwhile_ctrlc(prompt: str, callback: callable, *args, **kwargs):
    """
    Continuously prompts the user for input until a valid value is provided.
    
    Args:
        prompt (str): The prompt to display to the user.
        callback (callable): A callback function that will be called with the user's input.
    
    Returns:
        None
    """
    while True:
        try:
            callback(input(prompt), *args, **kwargs)
        except KeyboardInterrupt | EOFError:  # sometimes ctrl+c raises EOFError for some reason
            break
        except ContinueLoop as e:
            print(e)
            continue
        else:
            # continue as normal
            continue