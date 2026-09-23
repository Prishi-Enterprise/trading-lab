import { z } from "zod";

export const loginEmail = z.string().trim().toLowerCase().email().max(254);
export const loginCode = z.string().regex(/^\d{8}$/);

export type LoginState = {
  email: string;
  step: "email" | "code";
  sent?: number;
  error?: string;
  message?: string;
};
