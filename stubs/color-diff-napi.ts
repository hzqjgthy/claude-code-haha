// Local builds don't ship the native `color-diff-napi` addon, so the
// tsconfig path alias points this module name at our TypeScript port.
// Re-export the full implementation so callers get the same render() API.
export {
  ColorDiff,
  ColorFile,
  getNativeModule,
  getSyntaxTheme,
  type ColorDiffClass,
  type ColorFileClass,
  type NativeModule,
  type SyntaxTheme,
} from '../src/native-ts/color-diff/index.js'





// export type SyntaxTheme = {
//   name: string;
// };

// export class ColorDiff {
//   format(input: string): string {
//     return input;
//   }
// }

// export class ColorFile {
//   format(input: string): string {
//     return input;
//   }
// }

// export function getSyntaxTheme(themeName: string): SyntaxTheme {
//   return { name: themeName };
// }