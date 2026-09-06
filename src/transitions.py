import uasyncio as asyncio

# Default fade duration in milliseconds
DEFAULT_FADE_DURATION_MS = 500
# Number of steps for the fade/wipe effect
EFFECT_STEPS = 20
# Default wipe duration
DEFAULT_WIPE_DURATION_MS = 400


async def _fade(screen_manager, start_brightness, end_brightness, duration_ms):
    """Helper function to fade backlight."""
    delta = (end_brightness - start_brightness) / EFFECT_STEPS
    step_delay = duration_ms // EFFECT_STEPS

    current_brightness = start_brightness
    for _ in range(EFFECT_STEPS):
        current_brightness += delta
        # Clamp brightness between 0.0 and 1.0
        clamped_brightness = max(0.0, min(1.0, current_brightness))
        screen_manager.display.set_backlight(clamped_brightness)
        await asyncio.sleep_ms(step_delay)

    # Ensure final brightness is set exactly
    screen_manager.display.set_backlight(end_brightness)


async def fade_out(screen_manager, duration_ms=DEFAULT_FADE_DURATION_MS):
    """Fade the screen backlight out (to black)."""
    print("[Transition] Fading out...")
    try:
        # Ensure backlight is fully on before starting fade out
        screen_manager.display.set_backlight(1.0)
        await asyncio.sleep_ms(20)  # Small delay to ensure it takes effect
        await _fade(screen_manager, 1.0, 0.0, duration_ms)
        print("[Transition] Fade out complete.")
    except Exception as e:
        print(f"[Transition] Error during fade out: {e}")
        # Ensure backlight is off in case of error during fade
        screen_manager.display.set_backlight(0.0)


async def fade_in(screen_manager, duration_ms=DEFAULT_FADE_DURATION_MS):
    """Fade the screen backlight in (from black)."""
    print("[Transition] Fading in...")
    try:
        # Ensure screen starts black before fading in
        screen_manager.display.set_backlight(0.0)
        await asyncio.sleep_ms(50)  # Small delay to ensure backlight is off
        await _fade(screen_manager, 0.0, 1.0, duration_ms)
        print("[Transition] Fade in complete.")
    except Exception as e:
        print(f"[Transition] Error during fade in: {e}")
        # Ensure backlight is on in case of error during fade
        screen_manager.display.set_backlight(1.0)


def _wipe_rect(width, height, step, vertical, reverse):
    """
    The revealed/covered rectangle after `step` of EFFECT_STEPS, as
    (x, y, w, h). `vertical` wipes along the y axis, `reverse` starts at the
    right/bottom edge instead of the left/top one.
    """
    if vertical:
        h = (height * step) // EFFECT_STEPS
        return 0, (height - h) if reverse else 0, width, h
    w = (width * step) // EFFECT_STEPS
    return (width - w) if reverse else 0, 0, w, height


async def _wipe_out(screen_manager, label, vertical, reverse, duration_ms):
    """Wipe the current screen content out to black."""
    print(f"[Transition] Wiping out {label}...")
    display = screen_manager.display
    width, height = display.get_bounds()
    step_delay = duration_ms // EFFECT_STEPS
    black_pen = screen_manager.get_pen(screen_manager.theme["BACKGROUND_COLOR"])
    try:
        for step in range(EFFECT_STEPS + 1):
            x, y, w, h = _wipe_rect(width, height, step, vertical, reverse)
            display.set_pen(black_pen)
            display.rectangle(x, y, w, h)
            display.update()
            await asyncio.sleep_ms(step_delay)
        print(f"[Transition] Wipe out {label} complete.")
    except Exception as e:
        print(f"[Transition] Error during wipe out {label}: {e}")
        # Ensure screen is black in case of error
        display.set_pen(black_pen)
        display.rectangle(0, 0, width, height)
        display.update()


async def _wipe_in(screen_manager, applet_to_draw, label, vertical, reverse, duration_ms):
    """Wipe the new applet content in over black."""
    print(f"[Transition] Wiping in {label}...")
    display = screen_manager.display
    width, height = display.get_bounds()
    step_delay = duration_ms // EFFECT_STEPS
    black_pen = screen_manager.get_pen(screen_manager.theme["BACKGROUND_COLOR"])
    try:
        # Start with a black screen
        display.set_pen(black_pen)
        display.rectangle(0, 0, width, height)
        display.update()
        await asyncio.sleep_ms(50)  # Short delay

        for step in range(1, EFFECT_STEPS + 1):
            # Clip to the area revealed so far and redraw the applet in it.
            display.set_clip(*_wipe_rect(width, height, step, vertical, reverse))
            # Clear within the clip first to avoid overdraw artifacts
            display.set_pen(black_pen)
            display.clear()
            await applet_to_draw.draw()
            display.update()
            await asyncio.sleep_ms(step_delay)

        display.remove_clip()
        # Final full draw to ensure consistency
        await applet_to_draw.draw()
        display.update()
        print(f"[Transition] Wipe in {label} complete.")
    except Exception as e:
        print(f"[Transition] Error during wipe in {label}: {e}")
        # Perform a final, unclipped draw to ensure the full screen is correct
        display.remove_clip()
        await applet_to_draw.draw()
        display.update()
    finally:
        # Ensure the clip is always removed, even if errors occurred above
        screen_manager.display.remove_clip()


def _wipe(label, vertical, reverse):
    """Build the (exit, entry) transition pair for one wipe direction."""
    async def wipe_out(screen_manager, duration_ms=DEFAULT_WIPE_DURATION_MS):
        await _wipe_out(screen_manager, label, vertical, reverse, duration_ms)

    async def wipe_in(screen_manager, applet_to_draw, duration_ms=DEFAULT_WIPE_DURATION_MS):
        await _wipe_in(screen_manager, applet_to_draw, label, vertical, reverse, duration_ms)

    return wipe_out, wipe_in


# Dictionary mapping transition names to their functions (or None)
# We store tuples: (exit_transition_func, entry_transition_func)
# Entry transition functions might require the applet instance as the second argument.
TRANSITIONS = {
    "None": (None, None),
    "Fade": (fade_out, fade_in),
    "Wipe Left-To-Right": _wipe("LTR", False, False),
    "Wipe Right-To-Left": _wipe("RTL", False, True),
    "Wipe Top-To-Bottom": _wipe("TTB", True, False),
    "Wipe Bottom-To-Top": _wipe("BTT", True, True),
    # Add more transitions here in the future
}

# List of available transition names for the UI, in the desired order
AVAILABLE_TRANSITIONS = [
    "None",
    "Fade",
    "Wipe Left-To-Right",
    "Wipe Right-To-Left",
    "Wipe Top-To-Bottom",
    "Wipe Bottom-To-Top",
]
