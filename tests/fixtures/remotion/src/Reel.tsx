import {Sequence} from 'remotion';
const dynamicStart = 5 * 30;
export const Reel = () => (
  <>
    <Sequence from={0} durationInFrames={42} name="cold open">
      <div />
    </Sequence>
    <Sequence from={42} durationInFrames={48} name="title card">
      <h1>Seven rules nobody told you about editing reels fast and clean</h1>
    </Sequence>
    <Sequence durationInFrames={150} from={90} name="demo">
      <p>Rule one</p>
    </Sequence>
    <Sequence from={240} durationInFrames={90} name="b-roll" />
    <Sequence from={330} durationInFrames={90} name="cta">
      <Title text={"Follow for part 2"} />
    </Sequence>
    <Sequence from={420} durationInFrames={180} name="outro">
      <p>Thanks</p>
    </Sequence>
    <Sequence from={dynamicStart} durationInFrames={10} name="computed" />
  </>
);
