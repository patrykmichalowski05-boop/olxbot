Flip Hunter Mobile

Requirements:
- Node.js >=22.13
- Expo SDK 57
- HTTPS mobile API

Install on a development workstation:

cd mobile
npm install
npx expo install --fix
npx expo-doctor

cp .env.example .env

Set EXPO_PUBLIC_FLIP_API_URL to your HTTPS API URL.

npm run typecheck
npx expo start

Never put passwords, AI keys or backend secrets
inside EXPO_PUBLIC_ variables.

Mobile builds and push notifications
still require separate testing.
