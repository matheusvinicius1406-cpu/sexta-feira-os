namespace SextaFeira.UIEngine.Themes;

/// <summary>
/// Manages the current active theme and provides notifications
/// when the theme changes. All HUD components subscribe to theme
/// changes to re-render with updated colors and parameters.
/// </summary>
public class ThemeController
{
    private ITheme _currentTheme;

    /// <summary>
    /// Gets the currently active theme.
    /// </summary>
    public ITheme CurrentTheme => _currentTheme;

    /// <summary>
    /// Fired when the theme changes. UI components should
    /// re-render in response.
    /// </summary>
    public event Action<ITheme>? OnThemeChanged;

    /// <summary>
    /// Fired for individual property changes (less aggressive than full theme swap).
    /// </summary>
    public event Action<string, object?>? OnPropertyChanged;

    public ThemeController(ITheme initialTheme)
    {
        _currentTheme = initialTheme ?? NeonDarkTheme.Instance;
    }

    /// <summary>
    /// Applies a new theme to the HUD. Fires OnThemeChanged.
    /// </summary>
    public void ApplyTheme(ITheme theme)
    {
        if (theme == null) return;
        _currentTheme = theme;
        OnThemeChanged?.Invoke(_currentTheme);
    }

    /// <summary>
    /// Sets a single property on the current theme (for live customization).
    /// </summary>
    public void SetProperty(string propertyName, object? value)
    {
        OnPropertyChanged?.Invoke(propertyName, value);
    }

    /// <summary>
    /// Resets to the default Neon Dark theme.
    /// </summary>
    public void ResetToDefault()
    {
        ApplyTheme(NeonDarkTheme.Instance);
    }
}
