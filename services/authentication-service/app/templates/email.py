"""
Authentication Service — Email Templates (Checkpoint 3)

Provides OTP email template rendering for both HTML and plain-text formats.

Design decisions:
  - Pure string formatting — no third-party template engine dependency.
    Keeps the dependency footprint minimal and consistent with the project.
  - Both functions accept the same parameters and are independently renderable.
  - The OTP is embedded as a display value only. It is never logged by
    these functions.
  - recipient_name is optional: a personalised greeting is used when
    provided; a generic greeting ("Hello,") is used when omitted.
  - HTML template is intentionally kept compatible with major email clients
    (Outlook, Gmail, Apple Mail) using table-based layout and inline styles.

Public API:
    render_otp_html(otp, expiration_minutes, recipient_name) -> str
    render_otp_plain(otp, expiration_minutes, recipient_name) -> str
"""

from typing import Optional


def render_otp_html(
    otp: str,
    expiration_minutes: int,
    recipient_name: Optional[str] = None,
) -> str:
    """
    Render the HTML version of the OTP verification email.

    Args:
        otp:                The 6-digit verification code to display.
        expiration_minutes: Minutes until the OTP expires (shown in body).
        recipient_name:     Optional first name for personalised greeting.

    Returns:
        str: Complete HTML email body as a string.
    """
    greeting = f"Hello, {recipient_name}!" if recipient_name else "Hello,"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Verify your OntDekker email</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background-color:#f4f4f5;padding:40px 20px;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
               style="max-width:520px;background-color:#ffffff;border-radius:12px;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

          <!-- Header / brand -->
          <tr>
            <td align="center"
                style="background-color:#1a1a2e;padding:32px 40px 28px;">
              <span style="font-size:26px;font-weight:700;color:#ffffff;
                           letter-spacing:-0.5px;">
                Ont<span style="color:#e94560;">Dekker</span>
              </span>
              <p style="margin:8px 0 0;font-size:13px;color:#a0a0b0;
                        letter-spacing:0.5px;text-transform:uppercase;">
                Email Verification
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px 28px;">

              <p style="margin:0 0 16px;font-size:16px;color:#1a1a2e;line-height:1.6;">
                {greeting}
              </p>

              <p style="margin:0 0 28px;font-size:15px;color:#4a4a6a;line-height:1.6;">
                Use the verification code below to confirm your email address.
                This code is valid for <strong>{expiration_minutes} minutes</strong>.
              </p>

              <!-- OTP code block -->
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td align="center"
                      style="background-color:#f0f0f8;border-radius:8px;
                             padding:24px 16px;">
                    <span style="font-size:36px;font-weight:700;
                                 letter-spacing:10px;color:#1a1a2e;
                                 font-family:'Courier New',Courier,monospace;">
                      {otp}
                    </span>
                  </td>
                </tr>
              </table>

              <p style="margin:28px 0 0;font-size:13px;color:#7a7a9a;line-height:1.6;">
                This code expires in <strong>{expiration_minutes} minutes</strong>.
                Do not share it with anyone. OntDekker staff will never ask for
                this code.
              </p>

            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #ebebf0;margin:0;" />
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px 32px;">
              <p style="margin:0;font-size:12px;color:#9a9ab0;line-height:1.6;">
                If you did not request this verification, you can safely ignore
                this email. Your account remains secure.
              </p>
              <p style="margin:12px 0 0;font-size:12px;color:#9a9ab0;">
                &copy; OntDekker &mdash; Discover the world together.
              </p>
            </td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>
  <!-- /Outer wrapper -->

</body>
</html>"""


def render_otp_plain(
    otp: str,
    expiration_minutes: int,
    recipient_name: Optional[str] = None,
) -> str:
    """
    Render the plain-text fallback version of the OTP verification email.

    Args:
        otp:                The 6-digit verification code to display.
        expiration_minutes: Minutes until the OTP expires (shown in body).
        recipient_name:     Optional first name for personalised greeting.

    Returns:
        str: Plain-text email body as a string.
    """
    greeting = f"Hello, {recipient_name}!" if recipient_name else "Hello,"

    return f"""{greeting}

Use the verification code below to confirm your email address on OntDekker.

Your verification code:

    {otp}

This code expires in {expiration_minutes} minutes.

Do not share this code with anyone. OntDekker staff will never ask for this code.

If you did not request this verification, you can safely ignore this email.
Your account remains secure and no action is required.

---
OntDekker — Discover the world together.
"""
