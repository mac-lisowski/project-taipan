# Spec: Registration

Status: planned.

Seam: a registration module owns token rules over an injected
session. The shared email-delivery seam owns all mail sending with
a Resend adapter. Routers stay thin.

## Problem Statement

There is no self sign up. New users need an admin to make accounts. Growth needs open sign up. The flow must stay safe. Spam accounts must not get in. Passwords must not be set over an open form.

## Solution

The visitor enters an email only. The system sends an activation link by email. The link opens a set password page. The user sets a password. The system logs the user in at once. The web lands on /dashboard. Login keeps its form. Login also lands on /dashboard. All mail goes through the shared email delivery seam. Tokens are single use, hashed at rest, and short lived. Sessions reuse the existing sessions table pattern.

## User Stories

1. As a visitor, I want to sign up with my email only, so that I can start fast.
2. As a visitor, I want a clear note that a mail is on the way, so that I know what to do next.
3. As a visitor, I want to get an activation mail soon after sign up, so that I am not stuck.
4. As a new user, I want to open the activation link, so that I can set my password.
5. As a new user, I want to set my password on a plain page, so that I finish sign up.
6. As a new user, I want to be logged in right after I set my password, so that I skip a second login.
7. As a new user, I want to land on /dashboard after activation, so that I know where I am.
8. As a returning user, I want to log in with email and password, so that I get back in.
9. As a returning user, I want to land on /dashboard after login, so that login and activation agree.
10. As a signed in user, I want /dashboard to show my session works, so that I trust the login.
11. As a visitor with no session, I want /dashboard to send me to login, so that private pages stay shut.
12. As a user with a used link, I want a clear expired note, so that I can ask for a new mail.
13. As a user with an old link, I want the link to fail after expiry, so that old mails do not work forever.
14. As a user who clicks twice, I want the second use to fail, so that a link works one time only.
15. As a user with a bad link, I want a clear invalid note, so that I do not guess.
16. As an existing user, I want a new sign up with my email to resend safely, so that I am not locked out.
17. As an operator, I want no password stored before activation, so that half accounts cannot log in.
18. As an operator, I want token hashes at rest and not plain tokens, so that a leak shows less.

## Implementation Decisions

- Registration is split in two steps. Step one takes an email and mails a link. Step two takes the token plus a new password and makes the session.
- The registration module owns the token rules and the two endpoints. The web owns the two pages and the redirect to /dashboard. Neither side owns the other job.
- All mail goes through the one shared email delivery seam. The seam takes a template name plus typed data plus recipient. A Resend adapter backs prod. Registration calls the seam. It never calls a mail vendor direct.
- Activation tokens are random, single use, hashed at rest, and short lived. Plain tokens live only in the mailed link. The store holds hashes plus expiry plus used flags.
- The request endpoint always answers the same. It mails only for new mail. It never says if an email exists. This keeps user lists shut.
- The activation endpoint checks hash match, expiry, and unused state in one pass. It then marks the token used, sets the password hash, and makes a session. A replay of the same link fails.
- Password rules match login rules. One hasher and one check serve both paths. Activation sets the same hash login reads.
- Session handling reuses the existing sessions table pattern. Activation and login mint sessions the same way. The cookie shape and lookup stay one path.
- After activation the web lands on /dashboard. After login the web lands on /dashboard. One landing rule serves both flows.
- The set password page reads the token from the link. It posts token plus password. It shows invalid or expired states from the endpoint result. It never decides token state on its own.

## Testing Decisions

- API tests cross HTTP only with a real test database. They cover request with a fresh email, resend for the same email, same answer for known and unknown mail, and no mail vendor call past the seam.
- Token tests pin single use, hash at rest, and short expiry. They use a valid link once with success, reuse with failure, tampered link with failure, and old link with failure.
- Activation tests pin account effects. They check no login before password is set, login works after, landing target is /dashboard, and password checks match login.
- Mail tests use the fake adapter of the email delivery seam. They assert one send per new request, link holds the token, and no vendor SDK in the registration path.
- Web tests pin redirects and states. They check activation success lands on /dashboard, login success lands on /dashboard, no session on /dashboard sends to login, and bad links show invalid or expired notes.
- Web tests use pure choice functions with stubbed fetch. No full page render is needed for the redirect and state rules.

## Out of Scope

- Password reset and forgot flows.
- Invite only sign up and admin made accounts.
- Extra profile fields at sign up.
- Social login and passkeys.
- Rate limits and captcha.
- Org tenants and extra roles.
- Session rotation and device lists.

## Further Notes

- The visual lives beside this file in spec.html. It shows the module seam and the test seam.
- Cross spec pact holds. Mail uses the shared email delivery seam with a Resend adapter. Tokens are single use, hashed at rest, and short lived. The web lands on /dashboard after login or activation. Sessions reuse the existing sessions table pattern.
