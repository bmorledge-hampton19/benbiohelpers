# This script contains objects that are broadly useful for plotting, including my default text scaling and the blank background theme.
import plotnine

# Default text scaling
defaultTextScaling = plotnine.theme(plot_title = plotnine.element_text(size = 26, hjust = 0.5),
                                    axis_title = plotnine.element_text(size = 22), axis_text = plotnine.element_text(size = 18),
                                    legend_title = plotnine.element_text(size = 22), legend_text = plotnine.element_text(size = 18),
                                    strip_text = plotnine.element_text(size = 22), legend_key = plotnine.element_rect(color = "white", fill = "white"))

# Blank background theme
blankBackground = plotnine.theme(panel_grid_major = plotnine.element_blank(), panel_grid_minor = plotnine.element_blank(),
                                 panel_background = plotnine.element_blank(), axis_line = plotnine.element_line(color = "black"))