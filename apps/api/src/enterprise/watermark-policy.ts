export interface TenantWatermarkConfig {
  text?: string;
  opacity?: number;
  x_margin?: number;
  y_margin?: number;
  font_size?: number;
}

export interface ResolvedWatermarkConfig {
  text: string;
  opacity: number;
  x_margin: number;
  y_margin: number;
  font_size: number;
  enforced_minimum: true;
}

export function resolveTenantWatermarkConfig(tenantConfig: TenantWatermarkConfig | undefined, enterpriseMode: boolean): ResolvedWatermarkConfig {
  const minOpacity = Number(process.env.ENTERPRISE_WATERMARK_MIN_OPACITY ?? 0.2);
  const minMargin = Number(process.env.ENTERPRISE_WATERMARK_MIN_MARGIN ?? 12);
  const defaultText = process.env.WATERMARK_TEXT ?? "Goldman AI";

  if (!enterpriseMode) {
    return {
      text: defaultText,
      opacity: Math.max(minOpacity, Number(process.env.WATERMARK_OPACITY ?? 0.35)),
      x_margin: Math.max(minMargin, Number(process.env.WATERMARK_X_MARGIN ?? 24)),
      y_margin: Math.max(minMargin, Number(process.env.WATERMARK_Y_MARGIN ?? 24)),
      font_size: Math.max(12, Number(process.env.WATERMARK_FONT_SIZE ?? 22)),
      enforced_minimum: true
    };
  }

  return {
    text: tenantConfig?.text ?? defaultText,
    opacity: Math.max(minOpacity, tenantConfig?.opacity ?? Number(process.env.WATERMARK_OPACITY ?? 0.35)),
    x_margin: Math.max(minMargin, tenantConfig?.x_margin ?? Number(process.env.WATERMARK_X_MARGIN ?? 24)),
    y_margin: Math.max(minMargin, tenantConfig?.y_margin ?? Number(process.env.WATERMARK_Y_MARGIN ?? 24)),
    font_size: Math.max(12, tenantConfig?.font_size ?? Number(process.env.WATERMARK_FONT_SIZE ?? 22)),
    enforced_minimum: true
  };
}
