# Apple App Store Plan

This package is ready for GitHub Pages as a web app. Publishing to the Apple App Store is possible, but it requires an iOS/iPadOS app wrapper and additional product work.

## What Apple requires

As of March 22, 2026, the main Apple requirements we need to plan around are:

- Apple Developer Program membership. Apple says the annual fee is 99 USD for the Apple Developer Program.
- An app record and build uploaded through App Store Connect.
- App Review approval.
- A real app experience, not just a repackaged website. Apple’s App Review Guidelines section 4.2 says apps should go beyond a simple website wrapper.
- Current SDK requirements. Apple’s submission page says that starting April 28, 2026, iPhone and iPad apps uploaded to App Store Connect must be built with the iOS and iPadOS 26 SDK or later.

Official Apple references:

- https://developer.apple.com/help/account/membership/program-enrollment
- https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-workflow
- https://developer.apple.com/app-store/review/guidelines/
- https://developer.apple.com/app-store/submitting/
- https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/

## What we would need to build

The safest path is to turn Dinosaur Atlas into a real iOS app instead of a thin web wrapper.

Recommended next version:

- Native shell in SwiftUI for iPhone and iPad
- Embedded local database/assets for offline browsing
- Native map interactions and touch gestures
- Native navigation, search, favorites, and saved taxa
- App icon, launch assets, screenshots, and privacy disclosures
- Review notes and test credentials if any gated content is later added

## Why a plain wrapper is risky

If we only drop the current site into a `WKWebView`, Apple may view it as too close to a repackaged website under guideline 4.2. To improve approval odds, the iOS version should add native value such as:

- offline fossil atlas browsing
- saved collections or favorite dinosaurs
- polished iPad layout and touch-first navigation
- native share/export features
- downloadable updates or curated featured exhibits

## Submission checklist

- Enroll in the Apple Developer Program
- Build the iOS/iPadOS app in Xcode with the current required SDK
- Create the App Store Connect record
- Prepare screenshots for iPhone and iPad
- Write the product description, keywords, and support URL
- Complete privacy answers in App Store Connect
- Test through TestFlight
- Submit for App Review

## Recommended next technical step

If you want, the next iteration can be an `ios/` folder with a SwiftUI app that loads this atlas locally and is structured specifically for App Store submission.
