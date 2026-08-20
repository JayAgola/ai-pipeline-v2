import "./index.css";
import React from "react";
import {Composition} from "remotion";

import {HelloWorld, myCompSchema} from "./HelloWorld";
import {Logo, myCompSchema2} from "./HelloWorld/Logo";
import {AIVideoTemplate} from "./AIVideoTemplate";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Demo composition */}
      {/* <Composition
        id="HelloWorld"
        component={HelloWorld}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        schema={myCompSchema}
        defaultProps={{
          titleText: "Welcome to Remotion",
          titleColor: "#000000",
          logoColor1: "#91EAE4",
          logoColor2: "#86A8E7",
        }}
      /> */}

      {/* Logo demo */}
      {/* <Composition
        id="OnlyLogo"
        component={Logo}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        schema={myCompSchema2}
        defaultProps={{
          logoColor1: "#91EAE4" as const,
          logoColor2: "#86A8E7" as const,
        }}
      /> */}

      {/* Main AI Video Template */}
      <Composition
        id="AIVideoTemplate"
        component={AIVideoTemplate}
        fps={30}
        width={1920}
        height={1080}
        durationInFrames={900}
        calculateMetadata={async ({ props }) => {
          return {
            width: props.width ?? 1920,
            height: props.height ?? 1080,
            durationInFrames: props.durationInFrames ?? 900,
          };
        }}
        defaultProps={{
          width: 1920,
          height: 1080,
          title: "AI Automation in 2025",
          subtitle: "What every business needs to know",
          points: [
            "AI saves 10+ hours every week",
            "Automate content creation",
            "Use free AI APIs",
          ],
          clipFiles: ["scene_0.mp4", "scene_1.mp4", "scene_2.mp4"],
          channelName: "AI Business Insights",
          audioFile: "voice.mp3",
          durationInFrames: 300,
          titleDuration: 90,
          outroDuration: 60,
        }}
      />
    </>
  );
};