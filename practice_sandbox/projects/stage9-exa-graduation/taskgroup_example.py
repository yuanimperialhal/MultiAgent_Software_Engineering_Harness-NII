import asyncio


async def say_after(delay: float, what: str) -> str:
    """A simple async function that waits and then returns a string."""
    await asyncio.sleep(delay)
    return what


async def fail_soon() -> None:
    """A simple async function that immediately raises a ValueError."""
    raise ValueError("Something went wrong in a task!")


async def run_task_group_demo(include_failure: bool = True) -> None:
    """
    Demonstrates asyncio.TaskGroup behavior when one subtask fails.
    
    This function creates a TaskGroup with two tasks:
      - One that succeeds after a short delay.
      - Optionally, one that fails immediately with a ValueError.
    
    According to Python 3.12 docs, the TaskGroup will cancel the remaining
    tasks upon the first exception and raise an ExceptionGroup containing all
    exceptions that occurred.
    
    Args:
        include_failure: If True, includes the failing task; if False, only
                         successful tasks are scheduled.
    """
    print("Starting TaskGroup demo...")
    async with asyncio.TaskGroup() as tg:
        tg.create_task(say_after(1, 'success'))
        if include_failure:
            tg.create_task(fail_soon())
    print("All tasks completed successfully.")
