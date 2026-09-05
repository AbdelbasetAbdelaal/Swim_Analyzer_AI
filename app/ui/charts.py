import pandas as pd
import plotly.graph_objects as go

# Premium Neon/Dark Theme Colors
BACKGROUND_COLOR = "rgba(0,0,0,0)" # Transparent to fit Streamlit dark mode
GRID_COLOR = "#333333"
TEXT_COLOR = "#E0E0E0"
PRIMARY_CYAN = "#00F0FF"
SECONDARY_BLUE = "#0055FF"
ACCENT_PINK = "#FF007F"
ACCENT_ORANGE = "#FF8C00"

def apply_premium_layout(fig: go.Figure, title: str):
    """Applies a consistent, premium dark theme to a Plotly figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color=TEXT_COLOR, family="Inter, sans-serif")),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif"),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def create_performance_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Creates a premium line chart for Performance Score over time using Plotly.
    """
    # Historical sessions can legitimately have no score. Plot only measured
    # values rather than coercing unavailable measurements to zero.
    df = df[df["Score"].notna()].copy()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No measured performance scores available", showarrow=False, font=dict(size=14, color=TEXT_COLOR))
        return apply_premium_layout(fig, "Performance Score Progression")

    if "DateTime" not in df.columns:
        df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
        
    df = df.sort_values(by="DateTime")

    def format_hover_text(row: pd.Series) -> str:
        score = row.get("Score")
        score_text = f"{score:.1f}" if pd.notna(score) else "N/A"
        return (
            f"<b>Date:</b> {row.get('Date', '')} {row.get('Time', '')}<br>"
            f"<b>Score:</b> {score_text}<br>"
            f"<b>Confidence:</b> {row.get('Confidence', 'N/A')}<br>"
            f"<b>Stroke:</b> {row.get('Stroke', 'Unknown')}"
        )

    hover_text = df.apply(format_hover_text, axis=1)

    fig = go.Figure()
    
    # Glowing filled area under the line
    fig.add_trace(go.Scatter(
        x=df['DateTime'],
        y=df['Score'],
        mode='lines+markers',
        name='Performance Score',
        line=dict(color=PRIMARY_CYAN, width=4, shape='spline'),
        marker=dict(size=8, color=TEXT_COLOR, line=dict(color=PRIMARY_CYAN, width=2)),
        fill='tozeroy',
        fillcolor='rgba(0, 240, 255, 0.1)', # Faint cyan glow
        text=hover_text,
        hoverinfo="text"
    ))

    # Add trendline (moving average) if we have enough points (e.g., > 5)
    if len(df) >= 5:
        ma = df['Score'].rolling(window=3, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df['DateTime'],
            y=ma,
            mode='lines',
            name='Trend (3-Session Avg)',
            line=dict(color='rgba(0, 240, 255, 0.3)', width=5, dash='dot'),
            hoverinfo='skip'
        ))

    fig = apply_premium_layout(fig, "Performance Score Progression")
    
    min_sc = df['Score'].dropna().min()
    max_sc = df['Score'].dropna().max()
    y_min = max(0, min_sc - 10) if pd.notna(min_sc) else 0
    y_max = min(100, max_sc + 10) if pd.notna(max_sc) else 100
    fig.update_yaxes(title="Overall Score", range=[y_min, y_max])
    fig.update_xaxes(title="Session Date", fixedrange=False)
    return fig

def create_cycles_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Creates a premium bar chart for Completed Cycles over time.
    """
    if "DateTime" not in df.columns:
        df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
        
    df = df.sort_values(by="DateTime")

    hover_text = df.apply(
        lambda row: f"<b>Date:</b> {row.get('Date', '')} {row.get('Time', '')}<br>"
                    f"<b>Cycles:</b> {row.get('Cycles', '0')}<br>"
                    f"<b>Stroke:</b> {row.get('Stroke', 'Unknown')}",
        axis=1
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['DateTime'],
        y=df['Cycles'],
        name='Completed Cycles',
        marker_color=ACCENT_PINK, 
        marker_line_color=TEXT_COLOR,
        marker_line_width=1,
        text=hover_text,
        hoverinfo="text"
    ))

    fig = apply_premium_layout(fig, "Completed Cycles (Endurance Trend)")
    fig.update_yaxes(title="Cycles Completed", fixedrange=False)
    fig.update_xaxes(title="Session Date", fixedrange=False)
    
    return fig


def create_3d_skeleton_chart(raw_landmarks, frame_idx: int = 0) -> go.Figure:
    """
    Renders an interactive rotatable 3D Pose Skeleton using Plotly Scatter3d.
    """
    fig = go.Figure()

    if not raw_landmarks or len(raw_landmarks) < 25:
        fig.add_annotation(text="No 3D landmark data available for this frame",
                           showarrow=False, font=dict(size=14, color=TEXT_COLOR))
        fig.update_layout(paper_bgcolor=BACKGROUND_COLOR, plot_bgcolor=BACKGROUND_COLOR)
        return fig

    # MediaPipe pose connections for 3D skeleton rendering
    POSE_CONNECTIONS = [
        (11, 12), # Left Shoulder -> Right Shoulder
        (11, 13), (13, 15), # Left Arm
        (12, 14), (14, 16), # Right Arm
        (11, 23), (12, 24), # Torso sides
        (23, 24), # Pelvic Line
        (23, 25), (25, 27), # Left Leg
        (24, 26), (26, 28)  # Right Leg
    ]

    # Extract 3D coordinates (invert Y for 3D coordinate system)
    xs = [lm.x for lm in raw_landmarks]
    ys = [-lm.y for lm in raw_landmarks]
    zs = [-getattr(lm, 'z', 0.0) for lm in raw_landmarks]

    # Draw limb connection lines
    for p1, p2 in POSE_CONNECTIONS:
        if p1 < len(xs) and p2 < len(xs):
            fig.add_trace(go.Scatter3d(
                x=[xs[p1], xs[p2]],
                y=[ys[p1], ys[p2]],
                z=[zs[p1], zs[p2]],
                mode='lines',
                line=dict(color=PRIMARY_CYAN, width=6),
                showlegend=False,
                hoverinfo='none'
            ))

    # Joint landmark nodes
    fig.add_trace(go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode='markers',
        marker=dict(size=6, color=ACCENT_PINK, symbol='circle'),
        name='Joint Landmarks',
        hoverinfo='text',
        text=[f"Landmark {i}" for i in range(len(xs))]
    ))

    fig.update_layout(
        title=dict(text=f"🧊 360° Interactive 3D Skeleton (Frame {frame_idx})", font=dict(size=16, color=TEXT_COLOR)),
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=BACKGROUND_COLOR,
        margin=dict(l=0, r=0, t=40, b=0),
        scene=dict(
            xaxis=dict(title='X (Width)', backgroundcolor=BACKGROUND_COLOR, gridcolor=GRID_COLOR, showbackground=True),
            yaxis=dict(title='Y (Height)', backgroundcolor=BACKGROUND_COLOR, gridcolor=GRID_COLOR, showbackground=True),
            zaxis=dict(title='Z (Depth)', backgroundcolor=BACKGROUND_COLOR, gridcolor=GRID_COLOR, showbackground=True),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
        )
    )
    return fig


def create_3d_torsion_chart(frames: list) -> go.Figure:
    """
    Renders 3D Core Torsion timeseries chart across the video timeline.
    """
    timestamps = []
    torsions = []
    rolls_3d = []

    for f in frames:
        if f.is_valid and f.angles:
            t = f.timestamp_ms / 1000.0
            timestamps.append(t)
            torsion_val = f.angles.core_torsion_3d.value if f.angles.core_torsion_3d else 0.0
            roll_val = f.angles.body_roll_3d.value if f.angles.body_roll_3d else 0.0
            torsions.append(torsion_val)
            rolls_3d.append(roll_val)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps, y=torsions,
        mode='lines', name='3D Core Torsion (°)',
        line=dict(color=ACCENT_ORANGE, width=3)
    ))
    fig.add_trace(go.Scatter(
        x=timestamps, y=rolls_3d,
        mode='lines', name='Pose-Relative 3D Body Roll (°)',
        line=dict(color=PRIMARY_CYAN, width=3)
    ))

    fig = apply_premium_layout(fig, "🧊 Pose-Relative 3D Core Torsion & Roll Timeline")
    fig.update_yaxes(title="Angle (°)", range=[0, 90])
    fig.update_xaxes(title="Time (seconds)")
    return fig


def create_benchmark_percentile_chart(benchmark_result) -> go.Figure:
    """
    Renders horizontal bar chart of population percentiles across metrics.
    """
    if not benchmark_result or not getattr(benchmark_result, 'comparisons', None):
        fig = go.Figure()
        fig.add_annotation(text="No Population Benchmark Data Available", showarrow=False, font=dict(size=14, color=TEXT_COLOR))
        fig.update_layout(paper_bgcolor=BACKGROUND_COLOR, plot_bgcolor=BACKGROUND_COLOR)
        return fig

    metrics = []
    percentiles = []
    colors = []

    for name, comp in benchmark_result.comparisons.items():
        pct = getattr(comp, 'percentile', None)
        if pct is None:
            continue
        metrics.append(name.replace("_", " ").title())
        percentiles.append(pct)
        if pct >= 85:
            colors.append(PRIMARY_CYAN)
        elif pct >= 65:
            colors.append(ACCENT_ORANGE)
        else:
            colors.append(ACCENT_PINK)

    fig = go.Figure()
    if not metrics:
        fig.add_annotation(text="No validated percentiles available", showarrow=False, font=dict(size=14, color=TEXT_COLOR))
        return apply_premium_layout(fig, "Population Percentile Rankings")
    fig.add_trace(go.Bar(
        y=metrics,
        x=percentiles,
        orientation='h',
        marker_color=colors,
        text=[f"{p:.1f}th percentile" for p in percentiles],
        textposition='inside',
        hoverinfo='text'
    ))

    # Population Mean reference line (50th percentile)
    fig.add_vline(x=50, line_dash="dash", line_color=TEXT_COLOR, annotation_text="Population Mean (50th)", annotation_position="top left")
    # Elite Mean reference line (90th percentile)
    fig.add_vline(x=90, line_dash="dot", line_color=PRIMARY_CYAN, annotation_text="Elite Benchmark (90th)", annotation_position="top right")

    fig = apply_premium_layout(fig, "📊 Population Percentile Rankings")
    fig.update_xaxes(title="Percentile Rank (%)", range=[0, 100])
    return fig


def create_bell_curve_chart(metric_name: str, raw_value: float, mean: float, std: float, elite_mean: float) -> go.Figure:
    """
    Renders a Gaussian Normal Distribution Bell Curve showing athlete position vs population.
    """
    import numpy as np

    if any(value is None for value in (raw_value, mean, std, elite_mean)):
        fig = go.Figure()
        fig.add_annotation(text="Distribution unavailable: insufficient validated evidence", showarrow=False, font=dict(size=14, color=TEXT_COLOR))
        return apply_premium_layout(fig, f"Normal Distribution: {metric_name.replace('_', ' ').title()}")

    if std <= 0:
        std = 1.0

    x = np.linspace(mean - 3.5 * std, mean + 3.5 * std, 100)
    y = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)

    fig = go.Figure()
    # Bell Curve area
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode='lines',
        name='Population Distribution',
        line=dict(color=SECONDARY_BLUE, width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 85, 255, 0.15)'
    ))

    # Population Mean vertical line
    fig.add_vline(x=mean, line_dash="dash", line_color=TEXT_COLOR, annotation_text=f"Mean: {mean:.1f}")

    # Elite Mean vertical line
    fig.add_vline(x=elite_mean, line_dash="dot", line_color=PRIMARY_CYAN, annotation_text=f"Elite: {elite_mean:.1f}")

    # Athlete Position Marker
    ath_y = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((raw_value - mean) / std) ** 2)
    fig.add_trace(go.Scatter(
        x=[raw_value], y=[ath_y],
        mode='markers+text',
        name='Athlete Value',
        marker=dict(size=14, color=ACCENT_PINK, symbol='star'),
        text=[f" Athlete ({raw_value:.1f})"],
        textposition="top center"
    ))

    fig = apply_premium_layout(fig, f"📈 Normal Distribution: {metric_name.replace('_', ' ').title()}")
    fig.update_xaxes(title=metric_name.replace("_", " ").title())
    fig.update_yaxes(showticklabels=False, title="Probability Density")
    return fig


def create_benchmark_radar_chart(benchmark_result) -> go.Figure:
    """
    Renders a 5-axis Radar / Spider Chart comparing Athlete percentile profile against elite benchmark (90th percentile).
    """
    if not benchmark_result or not getattr(benchmark_result, 'comparisons', None):
        fig = go.Figure()
        fig.add_annotation(text="No Population Benchmark Data Available", showarrow=False, font=dict(size=14, color=TEXT_COLOR))
        fig.update_layout(paper_bgcolor=BACKGROUND_COLOR, plot_bgcolor=BACKGROUND_COLOR)
        return fig

    categories = []
    athlete_pcts = []

    for name, comp in benchmark_result.comparisons.items():
        if name == "performance_score":
            continue
        pct = getattr(comp, 'percentile', None)
        if pct is not None:
            categories.append(name.replace("_", " ").title())
            athlete_pcts.append(pct)

    if not categories:
        fig = go.Figure()
        fig.add_annotation(text="Radar chart unavailable: unvalidated demographic cohort", showarrow=False, font=dict(size=14, color=TEXT_COLOR))
        return apply_premium_layout(fig, "🕸️ Biomechanical Percentile Radar Profile")

    # Close the radar loop
    categories_loop = categories + [categories[0]]
    athlete_pcts_loop = athlete_pcts + [athlete_pcts[0]]
    elite_loop = [90.0] * len(categories_loop)
    mean_loop = [50.0] * len(categories_loop)

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=mean_loop, theta=categories_loop,
        mode='lines', name='Population Mean (50th)',
        line=dict(color=TEXT_COLOR, width=1.5, dash='dash')
    ))

    fig.add_trace(go.Scatterpolar(
        r=elite_loop, theta=categories_loop,
        mode='lines', name='Elite Target (90th)',
        line=dict(color=PRIMARY_CYAN, width=2, dash='dot')
    ))

    fig.add_trace(go.Scatterpolar(
        r=athlete_pcts_loop, theta=categories_loop,
        mode='lines+markers', name='Athlete Percentile',
        fill='toself', fillcolor='rgba(255, 0, 127, 0.2)',
        line=dict(color=ACCENT_PINK, width=3),
        marker=dict(size=6, color=ACCENT_PINK)
    ))

    fig.update_layout(
        title=dict(text="🕸️ Biomechanical Percentile Radar Profile", font=dict(size=18, color=TEXT_COLOR, family="Inter, sans-serif")),
        polar=dict(
            bgcolor=BACKGROUND_COLOR,
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR)),
            angularaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR))
        ),
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=BACKGROUND_COLOR,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    return fig
