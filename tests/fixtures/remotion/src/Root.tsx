import {Composition} from 'remotion';
import {Reel} from './Reel';
export const Root = () => (
  <Composition id="Demo" component={Reel} durationInFrames={600} fps={30} width={1080} height={1920} />
);
