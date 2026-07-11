import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { message } = await req.json();

  if (!message?.trim()) {
    return NextResponse.json({ error: "Empty message" }, { status: 400 });
  }

  const upstream = await fetch(`${BACKEND}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!upstream.ok) {
    const err = await upstream.json().catch(() => ({}));
    return NextResponse.json(
      { error: err.detail ?? "Backend error" },
      { status: upstream.status }
    );
  }

  const data = await upstream.json();
  return NextResponse.json(data);
}
