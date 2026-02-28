import { spawn } from "node:child_process";

export interface WatermarkStyle {
  text: string;
  x_margin: number;
  y_margin: number;
  opacity: number;
  font_size: number;
}

export function resolveWatermarkStyle(overrides?: Partial<WatermarkStyle>): WatermarkStyle {
  const minOpacity = Number(process.env.WATERMARK_MIN_OPACITY ?? 0.2);
  const minMargin = Number(process.env.WATERMARK_MIN_MARGIN ?? 12);

  return {
    text: overrides?.text ?? process.env.WATERMARK_TEXT ?? "Goldman AI",
    x_margin: Math.max(minMargin, overrides?.x_margin ?? Number(process.env.WATERMARK_X_MARGIN ?? 24)),
    y_margin: Math.max(minMargin, overrides?.y_margin ?? Number(process.env.WATERMARK_Y_MARGIN ?? 24)),
    opacity: Math.max(minOpacity, overrides?.opacity ?? Number(process.env.WATERMARK_OPACITY ?? 0.35)),
    font_size: Math.max(12, overrides?.font_size ?? Number(process.env.WATERMARK_FONT_SIZE ?? 22))
  };
}

export function buildWatermarkFilter(style: WatermarkStyle): string {
  return `drawtext=text='${style.text}':x=w-tw-${style.x_margin}:y=h-th-${style.y_margin}:fontsize=${style.font_size}:fontcolor=white@${style.opacity}`;
}

export async function applyWatermarkOverlay(inputPath: string, outputPath: string, style: WatermarkStyle): Promise<void> {
  const filter = buildWatermarkFilter(style);

  await new Promise<void>((resolve, reject) => {
    const child = spawn("ffmpeg", ["-y", "-i", inputPath, "-vf", filter, "-codec:a", "copy", outputPath]);
    child.once("error", reject);
    child.once("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`ffmpeg exited with code ${code}`));
    });
  });
}
