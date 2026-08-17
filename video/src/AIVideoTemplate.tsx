import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface Props {
  title: string;
  subtitle: string;
  points: string[];
  clipFiles: string[];
  channelName: string;
  audioFile?: string;

  durationInFrames: number;
  titleDuration: number;
  outroDuration: number;
}

const TitleCard: React.FC<{
  title: string;
  subtitle: string;
}> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const y = interpolate(frame, [0, 20], [40, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(135deg,#0f0c29,#302b63,#24243e)",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        padding: 80,
      }}
    >
      <div
        style={{
          fontSize: 72,
          fontWeight: 800,
          color: "white",
          opacity,
          transform: `translateY(${y}px)`,
          textAlign: "center",
        }}
      >
        {title}
      </div>

      <div
        style={{
          marginTop: 30,
          fontSize: 34,
          color: "#b794f4",
          opacity: interpolate(frame, [15, 35], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      >
        {subtitle}
      </div>
    </AbsoluteFill>
  );
};

const ContentScene: React.FC<{
  point: string;
  clipFile?: string;
}> = ({ point, clipFile }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill>
      {clipFile ? (
        <OffthreadVideo
          src={staticFile(clipFile)}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      ) : (
        <AbsoluteFill
          style={{
            background: "#222",
          }}
        />
      )}

      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          padding: 60,
          background:
            "linear-gradient(transparent,rgba(0,0,0,0.7))",
        }}
      >
        <div
          style={{
            color: "white",
            fontSize: 42,
            fontWeight: 600,
            opacity: interpolate(frame, [0, 15], [0, 1], {
              extrapolateRight: "clamp",
            }),
            transform: `translateY(${interpolate(
              frame,
              [0, 15],
              [20, 0],
              {
                extrapolateRight: "clamp",
              }
            )}px)`,
          }}
        >
          {point}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const OutroScene: React.FC<{
  channelName: string;
}> = ({ channelName }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame,
    fps,
    config: {
      damping: 10,
    },
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(135deg,#0f0c29,#302b63,#24243e)",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          color: "white",
          fontSize: 56,
          fontWeight: 700,
          transform: `scale(${scale})`,
        }}
      >
        Like • Share • Subscribe
      </div>

      <div
        style={{
          marginTop: 30,
          color: "#b794f4",
          fontSize: 34,
          opacity: interpolate(frame, [10, 30], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      >
        {channelName}
      </div>
    </AbsoluteFill>
  );
};

export const AIVideoTemplate: React.FC<Props> = ({
  title,
  subtitle,
  points,
  clipFiles,
  channelName,
  audioFile,
  durationInFrames,
  titleDuration,
  outroDuration,
}) => {
  if (points.length === 0) {
    return (
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          background: "black",
          color: "white",
          fontSize: 50,
        }}
      >
        No content
      </AbsoluteFill>
    );
  }

  const frame = useCurrentFrame();

  const contentDuration =
    durationInFrames -
    titleDuration -
    outroDuration;

  const contentFrame = Math.max(
    frame - titleDuration,
    0
  );

  const pointDuration = Math.max(
    Math.floor(contentDuration / points.length),
    1
  );

  const pointIndex = Math.min(
    Math.floor(contentFrame / pointDuration),
    points.length - 1
  );

  const showTitle = frame < titleDuration;

  const showContent =
    frame >= titleDuration &&
    frame < titleDuration + contentDuration;

  const showOutro =
    frame >= titleDuration + contentDuration;

  return (
    <AbsoluteFill>
      {audioFile && (
        <Audio src={staticFile(audioFile)} />
      )}

      {showTitle && (
        <TitleCard
          title={title}
          subtitle={subtitle}
        />
      )}

      {showContent && (
        <ContentScene
          point={points[pointIndex]}
          clipFile={clipFiles[pointIndex]}
        />
      )}

      {showOutro && (
        <OutroScene
          channelName={channelName}
        />
      )}
    </AbsoluteFill>
  );
};