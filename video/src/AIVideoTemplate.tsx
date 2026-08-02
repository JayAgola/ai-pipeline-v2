import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Audio,
  staticFile,
} from "remotion";

interface Props {
  title: string;
  subtitle: string;
  points: string[];
  channelName: string;
  audioFile?: string;
}

// Title Card Scene (0 - 90 frames = 3 seconds)
const TitleCard: React.FC<{title: string; subtitle: string}> = ({title, subtitle}) => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 20], [30, 0]);
  const subtitleOpacity = interpolate(frame, [20, 40], [0, 1]);

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
      justifyContent: "center",
      alignItems: "center",
      flexDirection: "column",
      padding: "60px",
    }}>
      <div style={{
        fontSize: 72,
        fontWeight: 800,
        color: "#ffffff",
        textAlign: "center",
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        lineHeight: 1.2,
        textShadow: "0 4px 20px rgba(0,0,0,0.5)",
      }}>
        {title}
      </div>
      <div style={{
        fontSize: 36,
        color: "#a78bfa",
        marginTop: 24,
        opacity: subtitleOpacity,
        textAlign: "center",
      }}>
        {subtitle}
      </div>
    </AbsoluteFill>
  );
};

// Content Scene — shows bullet points one by one
const ContentScene: React.FC<{points: string[]}> = ({points}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{
      background: "#0f0f1a",
      padding: "80px",
      justifyContent: "center",
      flexDirection: "column",
    }}>
      {points.map((point, i) => {
        const startFrame = i * 40;
        const opacity = interpolate(frame, [startFrame, startFrame + 20], [0, 1], {
          extrapolateRight: "clamp",
        });
        const x = interpolate(frame, [startFrame, startFrame + 20], [-40, 0], {
          extrapolateRight: "clamp",
        });

        return (
          <div key={i} style={{
            display: "flex",
            alignItems: "center",
            gap: 24,
            marginBottom: 40,
            opacity,
            transform: `translateX(${x}px)`,
          }}>
            <div style={{
              width: 12,
              height: 12,
              borderRadius: "50%",
              background: "#a78bfa",
              flexShrink: 0,
            }}/>
            <div style={{
              fontSize: 36 ,
              color: "#ffffff",
              lineHeight: 1.4,
            }}>
              {point}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// Outro Scene
const OutroScene: React.FC<{channelName: string}> = ({channelName}) => {
  const frame = useCurrentFrame();
  const scale = spring({frame, fps: 30, config: {damping: 12}});

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
      justifyContent: "center",
      alignItems: "center",
      flexDirection: "column",
    }}>
      <div style={{
        fontSize: 56,
        fontWeight: 700,
        color: "#ffffff",
        transform: `scale(${scale})`,
        textAlign: "center",
      }}>
        Like & Subscribe
      </div>
      <div style={{
        fontSize: 36,
        color: "#a78bfa",
        marginTop: 20,
        opacity: interpolate(frame, [10, 30], [0, 1]),
      }}>
        {channelName}
      </div>
    </AbsoluteFill>
  );
};

// MAIN COMPOSITION — ties all scenes together
export const AIVideoTemplate: React.FC<Props> = ({
  title,
  subtitle,
  points,
  channelName,
  audioFile,
}) => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();

  const titleDuration = 180;   // 3 seconds
  const contentDuration = points.length * 40 + 60;  // ~4-6 seconds
  const outroDuration = 60;   // 2 seconds

  const showTitle = frame < titleDuration;
  const showContent = frame >= titleDuration && frame < titleDuration + contentDuration;
  const showOutro = frame >= titleDuration + contentDuration;

  return (
    <AbsoluteFill>
      {audioFile && <Audio src={staticFile(audioFile)} />}
      {showTitle && <TitleCard title={title} subtitle={subtitle} />}
      {showContent && (
        <ContentScene
          points={points}
        />
      )}
      {showOutro && <OutroScene channelName={channelName} />}
    </AbsoluteFill>
  );
};