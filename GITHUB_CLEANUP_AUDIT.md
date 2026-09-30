# GitHub Cleanup Audit — 2026-09-30

Repository: `akhtarkhan15081983-dotcom/ARI-SMART-RO`

## Safety decision

This is an **audit only**. No branch, tag, release, artifact, or history was deleted or rewritten. Inventory returned **145 branches**. A branch is not considered deletable merely because its name looks old. Where merged state, unique commits, or latest commit date were not individually verified, the classification is `NEEDS_MANUAL_REVIEW` and the action is `DO_NOT_DELETE`.

Verified production baseline for this audit: `hardening/max-pro-5of5-2026-09-29` at `ac00a9b080e3bc0d851c2811bfd76944154b38c2`.

Current work branch: `feature/low-ram-ro-health-repo-cleanup-2026-09-30` (active; its tip advances during this audit).

Legend: `NV` = not individually verified in this non-destructive pass. `EXACT_DUP` = exact branch-tip SHA duplicate of the named retained reference, therefore no unique tip commit relative to that retained reference; deletion still requires explicit approval.

## High-confidence classifications

| Branch | Snapshot SHA | Class | Merged | Unique commits | Latest date | Suggested action | Risk |
|---|---|---|---|---|---|---|---|
| `main` | `ab866e5c2b14c73b16b4f8f0f3c6800ca7b6c36a` | MAIN | NV | NV | NV | KEEP | CRITICAL |
| `hardening/max-pro-5of5-2026-09-29` | `ac00a9b080e3bc0d851c2811bfd76944154b38c2` | PRODUCTION | N/A | N/A | NV | KEEP | CRITICAL |
| `feature/low-ram-ro-health-repo-cleanup-2026-09-30` | active | KEEP_ACTIVE | no | active | 2026-09-30 | KEEP | CRITICAL |
| `hotfix/admin-otp-testing-toggle-2026-09-27` | `ac00a9b080e3bc0d851c2811bfd76944154b38c2` | MERGED_SAFE_TO_DELETE | EXACT_DUP of production baseline | 0 vs baseline | NV | Candidate only after approval | LOW |
| `feature/employee-training-compliance-v1.0.17` | `329a42a0c83bcad204e59babde248f505327c1b5` | MERGED_SAFE_TO_DELETE | EXACT_DUP of release sibling | 0 vs release sibling | NV | Candidate only after approval | LOW |
| `release/employee-training-compliance-v1.0.17` | `329a42a0c83bcad204e59babde248f505327c1b5` | NEEDS_MANUAL_REVIEW | NV | NV | NV | RETAIN while sister candidate exists | MEDIUM |
| `feature/notification-offer-center-v1.0.16` | `ed1eb92e4433c4e4bc2602d4bde6b1877cc69a91` | MERGED_SAFE_TO_DELETE | EXACT_DUP of release sibling | 0 vs release sibling | NV | Candidate only after approval | LOW |
| `release/notification-offer-center-v1.0.16` | `ed1eb92e4433c4e4bc2602d4bde6b1877cc69a91` | NEEDS_MANUAL_REVIEW | NV | NV | NV | RETAIN while sister candidate exists | MEDIUM |
| `feature/trusted-engineer-onboarding-v1.0.18` | `d0c56f5138375b5e8024ece49c8e1c7e9e0e4703` | MERGED_SAFE_TO_DELETE | EXACT_DUP of release sibling | 0 vs release sibling | NV | Candidate only after approval | LOW |
| `release/trusted-engineer-onboarding-v1.0.18` | `d0c56f5138375b5e8024ece49c8e1c7e9e0e4703` | NEEDS_MANUAL_REVIEW | NV | NV | NV | RETAIN while sister candidate exists | MEDIUM |
| `release/v1.0.34-reconcile` | `0982b016ff4a512061b50563d6ff8a48e6108f99` | MERGED_SAFE_TO_DELETE | EXACT_DUP of `reconcile-final` | 0 vs retained sibling | NV | Candidate only after approval | LOW |
| `release/v1.0.34-reconcile-check` | `0982b016ff4a512061b50563d6ff8a48e6108f99` | MERGED_SAFE_TO_DELETE | EXACT_DUP of `reconcile-final` | 0 vs retained sibling | NV | Candidate only after approval | LOW |
| `release/v1.0.34-reconcile-ci` | `0982b016ff4a512061b50563d6ff8a48e6108f99` | MERGED_SAFE_TO_DELETE | EXACT_DUP of `reconcile-final` | 0 vs retained sibling | NV | Candidate only after approval | LOW |
| `release/v1.0.34-reconcile-pr` | `0982b016ff4a512061b50563d6ff8a48e6108f99` | MERGED_SAFE_TO_DELETE | EXACT_DUP of `reconcile-final` | 0 vs retained sibling | NV | Candidate only after approval | LOW |
| `release/v1.0.34-reconcile-final` | `0982b016ff4a512061b50563d6ff8a48e6108f99` | NEEDS_MANUAL_REVIEW | NV | NV | NV | RETAIN as duplicate-group anchor | MEDIUM |

## Remaining inventory — conservative classification

Every branch below is classified `NEEDS_MANUAL_REVIEW`; `merged=NV`, `unique=NV`, `latest-date=NV`, suggested action=`DO_NOT_DELETE`, risk=`HIGH` until a branch-vs-retained-base compare proves otherwise.

```text
aesthetic-store-home | 3432f0223f068de1c4b99844f59bd55ea32a32a5
aesthetic-store-home-v2 | 5bd2f31a195e2956daabc2c0b18889bdb9b385b7
andy-assistant | 845cc3dd56c66a7312d6f06361750433de9a7c60
attendance-security | efcddc10bc0bff42522b522c99b3ec761f2c73f6
audit/professional-review-2026-09-21 | dd8367ea3d96fa7fc42d33a27f52aea7ab8b621a
customer-app-completion | 0448387f513e1773ac354ec9b216191bdcce6c1b
customer-lifecycle-import-v1.0.13 | 3da11b023c65170cbb09fc5d5d3969a5a3712663
deploy/training-v1.0.27-backend | 72651b3341f5139b266bb13f6c5c17df8a27e7c1
deploy/v1.0.14-production-sync | 5493868f576bb37d7fcb6901506b7e003e808b9d
deploy/v1.0.16-production-safe-sync | 9fcc983b04a38cad7e1fcb4cae64c932f90d36a9
deploy/v1.0.48-production | 10f475e78610d90c1d6454c7b66f906ff8d044b6
deploy/work-hours-v1.0.28-backend | a8173fe5f310631927c4d5aa3780acf106bacc3f
deploy/30-day-hindi-training-production-2026-09-21 | 9395c5440625966e103268812356b75345aed851
deploy-customer-lifecycle-v1.0.13 | 11252d61069a3f88c2ae205eb6284798b672e53f
deploy-exact-excel-customers-2026-09-18 | dbe80b732181e9ca26d74dface5b5f076eb2f984
deploy-office-calling-backend-2026-09-18 | 39a5ace982d9e5f3f3e5639d8b90dfc9c38058a8
deploy-remove-old-992-customers-2026-09-18 | e2027059ceeea24932661c1dbd90f95acc7d9c4d
exact-excel-customer-import-2026-09-18 | 604b85b804109883bcbce270da2ef227ad26e153
feat/admin-attendance-device-override-2026-09-17 | 0d1af3de564679abcfb8c806b4f647a4dc2b8356
feat/customer-admin-job-otp-display | 4a46efacce69152302ae1374986fba4d7efded5d
feat/customer-edit-and-status-controls | 14e2dc38359640cd1a51b5af2ff066d2553a189a
feat/customer-edit-delegation-20260921 | e0f8cb371600f2576955d99473a9415ac0e79281
feat/staged-employee-training-20260921 | f5839fc79fbd463af367b50d50b382f8085647a7
feat/windows-desktop-v1.0.30-2026-09-22 | c656ce90f2ff8559d76c16eb3e33c16b30ab5810
feat/windows-enterprise-ui-v1.0.31-2026-09-22 | b2db6a056bb325050fdf518f4a230104db2d7308
feat/windows-installer-v1.0.33 | 17a4120549da33aeec16fbed0834e9be8d34a2f4
feature/admin-approved-password-reset-2026-09-20 | 83affdfb3434798188ec83c3a44dea326fd599d0
feature/assign-customer-filters | fd8d804ea7a401b292c3960e4eaa683393aec5d9
feature/company-referral-wallet | ee6b6286b350ffb33a90b97c7c0c94858e546c26
feature/corporate-hrms-v1.0.15 | ee5e15ee0f8310930614b64b67ea18cfecd55c92
feature/customer-bulk-import-qr | 70b3fefc3d4e63b2d446f934db291bde83a8fd79
feature/customer-edit-all-fields-2026-09-26 | ec8fa32e74b2c346e535101b365088bbcad15979
feature/digital-rent-collection-2026-09-26 | e297f99fda87993fbb7368be3893d6ba3fb0b625
feature/digital-ro-passport | 729b2974e30eb8b50fd7e83edb66c04a5884c52f
feature/digital-ro-passport-phase2-2026-09-26 | 143e28af308582567d80314bebf32a7fd256a80a
feature/employee-hours-overtime-reports-v1.0.28 | d87b1133f53e03f68169ae75b86d1ea1f5c1ff4b
feature/employee-rent-collection | 3a13ff22f332d5514b09ec9a887e808422dc2638
feature/enterprise-hrms-command-center-2026-09-20 | 206233e01a57579b6f5c9de65b09f91023fe9fca
feature/fix-attendance-selfie | ec2674c1531bf16b91cab47711b89af66628b997
feature/free-sim-sms-gateway | cbd37e997c8399ec7fd950596bc4c891ffa29128
feature/global-search-filters-v1.0.9-2026-09-18 | c2b905181193328a499bd4516055c0d04aedc4b8
feature/harden-complaint-jobs-service-workflows-2026-09-24 | 4a91f7899f253545ea578c5fc1a649f08b6f880f
feature/inactive-and-single-customer-offers-2026-09-26 | 4a40dda153ddfd0a6203dfd0b95f9bbeb333ecd6
feature/inventory-optional-receipt-batch-qr-v1.0.45 | cf3b5728728a9c2ab73f98aab840a38177b0f04c
feature/posthog-observability | 85020fd8357284196758e17dc7765e4b4b6652a0
feature/production-readiness | d05455422cf78f2295225b76b3d21e560a248912
feature/ro-visual-parts-passport-2026-09-26 | 47c46a9edab4429816c3c9d12ec7260484c1debe
feature/session-auto-refresh | 5ac687fb992721ea5a046a18aa88c64444c239bb
feature/training-academy-v1.0.27 | e75727cb8a7b274b0b0112330cb690422c19237e
feature/unified-parts-ro-workflow-2026-09-23 | a4a854c07df9fd23a3b5b68f4f26852f663efc88
final-5-percent-completion | 5f53568b8c641a142a93e0dc45a6c45f8fad76d7
fix/android-reenrollment-auth-2026-09-23 | a98a0f7924be93be2c15a4037c7a3bcb4e5f51a1
fix/android-v1.0.31-universal-and-split-apks | e9d416346d7934b15032d385968f4b6e681e9fc4
fix/assigned-work-visibility-and-service | 03635c162a9a211a403024fe4a9bbc701137d739
fix/attendance-device-reliability-v1.0.46-2026-09-28 | 0d6cab6f7e10b17e5a0c1603ae37686af84fe1f3
fix/attendance-selfie-cross-device-2026-09-17 | fcfbcba12403dac420a875df52a71785d239aae8
fix/attendance-universal-android-v1.0.7 | dd8fe64feb04e55f837ea2347c6f1a3b6e19da79
fix/caller-customer-sync-20260921 | e515045300420134fe269f4adb18c09625193e80
fix/canonical-device-identity | 2a1dff2116ca1108b0ee2c4c6dede5fc1285bf16
fix/complaint-assignment-state | 1820daf9e4b95a3ddc03aca5e4a9b84afedf5845
fix/customer-data-original-serial-order | 0861d9812b99da96647b8cdb52b370e2ed86e813
fix/customer-list-scroll-state-v1.0.47-2026-09-28 | b920030232159596efe65ac1d8198e09ce12293b
fix/customer-old-card-serial-order | 757a530474ec7b4b221cd98fcc4d6f02832513c6
fix/device-migration-customer-scroll-v1.0.47-2026-09-28 | 838abf659637d0fd3e834988cd7f73fc02dacb62
fix/employee-map-v1.0.30-2026-09-22 | 6f968f79eab5ef2069712a0314eead2de0529226
fix/face-reenrollment-reliability | ccfdc7e69b9215f87e097ef36621bfa04783d2f1
fix/leave-single-date-installation-600 | 5c3494aa0346490f83b7ffae4e7680c8cdb453f2
fix/live-location-v2-2026-09-22 | 98875e9dcbd272bfd26d94650feaf47034d09730
fix/office-all-customers-complaints | 3851488f5efea59b3ef252d5055e4282ccc64048
fix/play-protect-sms-permission-v1.0.44-2026-09-27 | 160080f775e6c33fd92b338fc38ab6f42653ec93
fix/redmi-8a-low-memory-compat | 6d1c31419c573d2f7cf9effccc04ccf47089e441
fix/redmi-selfie-location-status-2026-09-20 | 91dd953b04517a0e2fa38354190606acbedab677
fix/tabbar-contrast-2026-09-23 | d32b6b3c8b7c17864c229cd3260faf20c2020c3f
fix/v1.0.25-customer-edit-crash | 8498309bb3318c9763fbe53ed557b241faa1c7f7
fix/vivo-s20-selfie-v103 | 41547bf24f8a1bb07e2fb7e1e1b2ac171e43fbf2
fix/vivo-s20-selfie-v104 | 5f5655a62387aad605bfa3f22011bcb6839df04f
fix/windows-responsive-pointer-2026-09-27 | 912dfde9dcc8e3538c6369d131d6f614fea07a67
fix/windows-safe-v1.0.32-2026-09-22 | 3feb46166fc2a1a2dce84feb37215b3c54d6617f
fix-employee-filter-overflow-v1.0.11 | 5ee2987da6f322dc5575ee92c6bf0df1b06bf8ee
fix-face-device-backend-2026-09-18 | 75aee852912f7117d55dc072189659bb5fa6cb3d
fix-latest-customer-import-v1.0.13 | ba64b10ad31c7584befbbe5eb58fd8df24576db9
fix-part-request-overflow-v1.0.10 | 47b23bb0c8c484d9a9734cf39c5afee08a7eb42f
fix-prod-customer-import-v1.0.13 | feafd65b888847e9d64096ffb22a62c02d8c5818
hardening/ci-version-consistency-2026-09-22 | cd8a9a73d6abbef0cbfe28320a32457bd4e2d38b
hardening/ci-version-consistency-v2-2026-09-22 | 0812db8b83112bcfba8548e9124c6464ed6926fb
hardening/client-observability-2026-09-22 | 289e31a974c6889d082a6f85e6be91105e524375
hardening/client-observability-v2-2026-09-22 | 6094536b2b06677adea35f90d3ef0d8073488791
hardening/deterministic-otp-tests-2026-09-22 | b0d5865aa2968e8db549303e625aa6becb110dff
hardening/deterministic-otp-tests-v2-2026-09-22 | c1ea1dd385d0ba8d2f9700448a9fe16384527899
hardening/device-health-center-2026-09-22 | 9a15a943da785a81e99fb4a078a3730304fcebec
hardening/global-audit-trail-2026-09-22 | db7badbaf1f6589c0c77d3e80e2c0f5590a75d93
hardening/offline-idempotency-2026-09-22 | 2f0772ee33bc34e34b28a338b5e236685ecf714b
hardening/startup-performance-2026-09-22 | 01273af9fd57500de4c4ee417b1712a698e6e994
hardening/startup-performance-v2-2026-09-22 | d8b5c31ffbc9f5abd5a2a418ab52af1fd93bcfde
hardening/strict-android-release-2026-09-22 | ab5755a12e6e9fff001e193bebe5590ae5ec439c
hardening/strict-android-release-v2-2026-09-22 | 6d95e91e6fbb70f13c0bfd2a0fae8e93c7b38698
hotfix/customer-self-service-v1.0.41 | 9cd9a977a8ccf481717eef00677adfcc46cdf50b
hotfix/employee-rent-permission | f84eb833b2183935ce3f307d0edfb99b90c2ada2
hotfix/v1.0.16-backend-green | 60ace30ae71a074e826e224e9d0b008447e09afc
hotfix/v1.0.16-notification-build | 2ab8dff131efd08bed6dfe51f3980f1c498020bd
hotfix/v1.0.35-assigned-customers | e31c5b90d3d8a8a04becc76665b90a6c9fba7c7b
hotfix/v1.0.38-backfill-job-ids | 73a23acbe7a63e4e9c39608af9c6eb01ab76a85d
integrate-saas-ops-2026-09-03 | f6182fee3f14151601c3f2a7440a87c18c99864c
milestone-95-integration | bc0c1dfdf1304e5a3149c3e6a95373090daa5c63
office-calling-desk-v1.0.12 | 3da6a4deea688a8e4cd3cd78d2fb5359fe3cdac3
production-blockers-fix | 0898efc903953ca72506ae569b690f1ec6c5b37b
production-launch | 5e2185dd5af8b7a26ceb8d819224ae465436ff9e
refactor/foundation-v2-2026-09-22 | 6c838dfabbb9c97cf7e51effe215db02baa149b7
referral-ui-integration | 28796532ab866d97513fe2b768b43c7139fc5d62
release/android-color-reenroll-2026-09-23 | 53fb6e39e9309cf9b8eedbdb3767e20abe559da9
release/certificate-pdf-v1.0.24 | 84b593618a525d0c619a00930642cb38944b1236
release/corporate-training-v1.0.22 | cc3b065db5ed91ffd8fe3a515b333e34f43837f7
release/integrated-v1.0.8-2026-09-18 | 0bb36d17916bead9c808633b64462d33b5f4eab1
release/offline-field-work-v1.0.21 | e14bd10a46c03e8125e755caf09dfa6dac3d3971
release/training-certification-v1.0.23 | 42684f5107d113f580aa1c5aaec226226f471b36
release/v1.0.34-production-sync | 72772db55d1d9669c63e5e1080876a232197d9b6
release/v1.0.34-signed | 015929f0ea1e20799d53c26e562c816680a7d16f
release/v1.0.36-prep | cffd7e4e140143eb2435004a029f07fb8fec18ec
release/v1.0.43-2026-09-26 | 64cd720156594aa2b84fcb8ae3522954f7423154
release-andy-coming-soon-2026-09-13 | be9bb6cf7f40e8c1bcd5eef3c72260a96a8f80ea
release-branding | 8d9f0ab658ec297784640d6011cb811fe9cdc510
remove-old-992-customers-2026-09-18 | 65a2a9bd52130aa726746b876bb31b83d6d71273
reports-center | 69e0567c2c619bb2873654f1000c41f45c599cfe
secure-exact-excel-payload-2026-09-18 | fbf6463434a1d53a2da2ec8780906c4c57baf91c
security/hardening-v1.0.41-2026-09-26 | 27f06fe552a14ef0ca67512dc4109d5208e86d17
security/hardening-v1.0.43-2026-09-26 | fb6f34db4286144b3afa47d794a91d2d952a6869
security/single-device-login-v1.0.26 | e4bcb0221dc112b69547aec033dfc7754b7aa9c2
sync/andy-assistant-to-main-2026-09-24 | 9854e73c9419ce4b91a6cd42cff9f6ca6128edea
test/admin-otp-bypass-2026-09-26 | 9d855dff81e2f7c783b69b04a0ff0c4fad7e5184
whatsapp-friendly-apk-v1.0.13 | cf14994a574a551e5499d100dc15c4969e483b2b
```

## Next audit pass before any deletion

For every `NEEDS_MANUAL_REVIEW` branch, fetch the latest commit date and compare it against both `main` and the verified production baseline. Record ahead/behind and unique commit counts. Only after that evidence exists should a branch move to `MERGED_SAFE_TO_DELETE`, `OBSOLETE_SAFE_TO_DELETE`, or `UNIQUE_UNMERGED_WORK`.

**No deletion is authorized by this file.**
