# Support Triage Agent — Consolidated Ticket Results

Consolidated from all 22 per-ticket files in `outputs/results/*.json` — one row per ticket run through the full LangGraph pipeline (`ingest -> sentiment_policy_check -> rag_retrieve -> draft_answer -> route -> confidence_recheck -> hitl_gate`). Reviewer fields reflect the latest row in `outputs/databases/triage.db`.

> An interactive HTML version of this report (charts, search/filter, click-to-expand rows) lives alongside this file at [`consolidated_report.html`](./consolidated_report.html) — open it locally in a browser. GitHub renders `.html` files as source, not as a page, so this Markdown version is the one meant to be read here.

## 1. Overview

| Metric | Value |
|---|---|
| Total tickets | **22** |
| AUTO_RESOLVE | 5 (23%) |
| ASK_INFO | 6 (27%) |
| ESCALATE | 8 (36%) |
| REFUSE | 3 (14%) |
| Avg groundedness (retrieval-similarity, 0–1) | 0.474 |
| Citation presence (of 5 AUTO_RESOLVE drafts) | 100% |
| Fabricated citations | 0 (none detected) |
| Reviewer approved | 22/22 (latest `triage.db` `reviewer_action`) |

## 2. Sentiment distribution

| Sentiment | Count |
|---|---|
| neutral | 11 |
| negative | 9 |
| abusive | 2 |

## 3. Groundedness scores

Phase-1 retrieval-similarity groundedness (`groundedness_score`), across all 22 tickets, against the configured threshold of **0.28** (`config/app_config.yaml`):

- **Mean:** 0.474
- **Min:** 0.172 (TCK-1017)
- **Max:** 0.652 (TCK-1019)
- **Below threshold:** 3 (TCK-1009, TCK-1017, TCK-1018)

## 4. All tickets

| Ticket | Category | Sentiment | Route | Reason | Groundedness | LLM judge | Citation | Reviewer |
|---|---|---|---|---|---:|---:|---|---|
| **TCK-1001** | refund_request | neutral | ESCALATE | low_confidence_after_retries | 0.572 | 0.95 | ✓ cited | APPROVED |
| **TCK-1002** | refund_request | negative | ESCALATE | repeat_refund_request_within_window | 0.604 | — | ✓ cited | APPROVED |
| **TCK-1003** | refund_request | negative | ESCALATE | refund_outside_window | 0.584 | — | ✓ cited | APPROVED |
| **TCK-1004** | subscription_cancellation | neutral | AUTO_RESOLVE | policy_grounded_response | 0.607 | 1.00 | ✓ cited | APPROVED |
| **TCK-1005** | login_access | neutral | ASK_INFO | missing_required_fields | 0.473 | — | ✓ cited | APPROVED |
| **TCK-1006** | login_access | neutral | ASK_INFO | missing_required_fields | 0.599 | — | ✓ cited | APPROVED |
| **TCK-1007** | troubleshooting | negative | ASK_INFO | classifier_requires_more_info | 0.312 | — | ✓ cited | APPROVED |
| **TCK-1008** | troubleshooting *(detected: refund_request)* | negative | ESCALATE | refund_outside_window | 0.472 | — | ✓ cited | APPROVED |
| **TCK-1009** | abusive_content *(detected: other)* | abusive | REFUSE | abusive_content_detected | 0.215 | — | no citation | APPROVED |
| **TCK-1010** | abusive_content *(detected: refund_request)* | negative | REFUSE | refund_abuse_language_detected | 0.633 | — | no citation | APPROVED |
| **TCK-1011** | refund_request | negative | AUTO_RESOLVE | policy_grounded_response | 0.648 | 1.00 | ✓ cited | APPROVED |
| **TCK-1012** | refund_request | neutral | ASK_INFO | missing_required_fields | 0.492 | — | ✓ cited | APPROVED |
| **TCK-1013** | troubleshooting | negative | ASK_INFO | classifier_requires_more_info | 0.351 | — | ✓ cited | APPROVED |
| **TCK-1014** | subscription_cancellation | neutral | ASK_INFO | missing_required_fields | 0.390 | — | ✓ cited | APPROVED |
| **TCK-1015** | subscription_cancellation *(detected: refund_request)* | negative | ESCALATE | refund_outside_window | 0.644 | — | ✓ cited | APPROVED |
| **TCK-1016** | subscription_cancellation | neutral | AUTO_RESOLVE | policy_grounded_response | 0.476 | 1.00 | ✓ cited | APPROVED |
| **TCK-1017** | other | neutral | ESCALATE | low_groundedness | 0.172 | — | ✓ cited | APPROVED |
| **TCK-1018** | other *(detected: login_access)* | neutral | ESCALATE | low_groundedness | 0.259 | — | ✓ cited | APPROVED |
| **TCK-1019** | login_access | neutral | AUTO_RESOLVE | policy_grounded_response | 0.652 | 1.00 | ✓ cited | APPROVED |
| **TCK-1020** | login_access | negative | ESCALATE | policy_mandated_escalation_keywords | 0.508 | — | ✓ cited | APPROVED |
| **TCK-1021** | abusive_content *(detected: other)* | abusive | REFUSE | abusive_content_detected | 0.300 | — | no citation | APPROVED |
| **TCK-1022** | troubleshooting | neutral | AUTO_RESOLVE | policy_grounded_response | 0.455 | 1.00 | ✓ cited | APPROVED |

## 5. Per-ticket details

Draft reply, retrieved sources, and reviewer notes for each ticket (collapsed by default — click to expand).

<details>
<summary><strong>TCK-1001</strong> — Refund request for annual plan (ESCALATE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us about your refund request for order ORD-1002. According to our refund policy [source: refund_policy.md], refund requests are accepted only within 7 days of the original purchase date. Since you were charged yesterday, your request is within the eligible timeframe.

However, refunds for annual plans are reviewed case by case and may be denied if the plan was already used for a significant period [source: refund_policy.md]. We would like to review your case further.

Could you please provide more information about your reason for requesting a refund? Additionally, we will review your account and order details to determine the best course of action.

If our standard policy cannot be applied to your situation, we may need to escalate your request to a specialist [source: refund_policy.md].

Thank you for your patience and cooperation.

Best regards,
Support Team
```

**Retrieved sources:** refund_policy.md, subscription_policy.md, troubleshooting_faq.md

**Reviewer** (review_id 59): APPROVED

</details>

<details>
<summary><strong>TCK-1002</strong> — Need refund again (ESCALATE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us regarding your refund request for order ORD-2091. According to our refund policy [source: refund_policy.md], if a customer submits multiple refund requests for the same order within 90 days, the case should be flagged as a repeat request and escalated to a specialist.

Since you have already requested a refund last month and are now requesting it again, this case will be escalated to a specialist for further review [source: refund_policy.md]. We apologize for any inconvenience caused by the delay in your previous refund request.

Please allow us to escalate this matter to ensure it is handled properly. We will review your case and get back to you as soon as possible.

Thank you for your patience and understanding.

Best regards,
Support Team
```

**Retrieved sources:** refund_policy.md

**Reviewer** (review_id 60): APPROVED

</details>

<details>
<summary><strong>TCK-1003</strong> — Refund after 10 days (ESCALATE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us regarding your refund request for order ORD-3007. According to our refund policy [source: refund_policy.md], refund requests are accepted only within 7 days of the original purchase date. Since your subscription renewed 12 days ago, your request is outside the standard 7-day refund window [source: refund_policy.md].

As per our escalation guidance [source: refund_policy.md], we recommend escalating this case because the refund request is outside the 7-day window. We will review your case, but please note that refunds for annual plans are reviewed case by case and may be denied if the plan was already used for a significant period [source: refund_policy.md].

We will escalate your request to a specialist for further review. They will be in touch with you to discuss the possibilities of a refund.

Thank you for your understanding.

Best regards,
Support Team
```

**Retrieved sources:** refund_policy.md

**Reviewer** (review_id 3): APPROVED

</details>

<details>
<summary><strong>TCK-1004</strong> — Cancel my subscription (AUTO_RESOLVE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to cancel your subscription. According to our subscription policy [source: subscription_policy.md], cancellation requests are effective at the end of the current billing period unless otherwise stated by the account settings. We will process your cancellation request for subscription SUB-4410, and it will be effective at the end of your current billing period.

Please note that as per our policy [source: subscription_policy.md], no refund is guaranteed for the current billing period. If you have any further questions or concerns, please don't hesitate to reach out.

Best regards,
[Your Name]
```

**Retrieved sources:** subscription_policy.md, troubleshooting_faq.md

**Reviewer** (review_id 55): APPROVED

</details>

<details>
<summary><strong>TCK-1005</strong> — Cannot sign in (ASK_INFO)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us about the issue with signing in to your account. To assist you with accessing your profile, I would like to troubleshoot the common issues first. According to our account access FAQ [source: account_access_faq.md], if you're having login problems, please confirm the email address used for registration. Additionally, if you've had repeated failed attempts, please wait 15 minutes before trying again as the account may be locked out [source: account_access_faq.md].

To better assist you, could you please provide one of the following if not already provided: the registered email address, the account ID, or the most recent order ID [source: account_access_faq.md]? This information will help us verify your account ownership and troubleshoot the issue further.

If the issue persists after trying the above steps, we may need to escalate this to our support team for further assistance [source: account_access_faq.md]. 

Please let me know if there's any additional information I can assist you with.

Best regards,
Support Team
```

**Retrieved sources:** account_access_faq.md, troubleshooting_faq.md

**Missing fields:** account identifier, error description

**Reviewer** (review_id 5): APPROVED — asking for user info to confirm identity

</details>

<details>
<summary><strong>TCK-1006</strong> — Reset password (ASK_INFO)</summary>

**Draft reply:**

```
Draft Reply:

To reset your password, you can use the password reset link on the login page [source: account_access_faq.md]. This should allow you to create a new password and regain access to your account. If you have any issues with this process or need further assistance, please let me know and I'll be happy to help. 

Before proceeding, could you please confirm your registered email address, account ID, or most recent order ID for verification purposes [source: account_access_faq.md]?
```

**Retrieved sources:** account_access_faq.md, troubleshooting_faq.md

**Missing fields:** account identifier

**Reviewer** (review_id 6): APPROVED

</details>

<details>
<summary><strong>TCK-1007</strong> — App keeps crashing (ASK_INFO)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us about the issue with the app crashing when you open the dashboard. To troubleshoot this issue, we can start by checking if the problem is related to your browser or internet connection. According to our troubleshooting FAQ [source: troubleshooting_faq.md], if the app is not loading, we should first ask you to refresh the browser and check the internet connection.

However, since you've mentioned that the app crashes after opening the dashboard, which is a more specific issue, we may need more information to diagnose the problem. As per our guidelines [source: troubleshooting_faq.md], we typically ask for more details such as the device or browser being used, the date the issue started, the exact error message, or the account identifier to better understand the issue.

Given that the issue is related to a technical problem that may require more in-depth investigation, especially considering it started after the latest update, we may need to escalate this issue for further assistance [source: troubleshooting_faq.md]. 

We recommend escalating this issue to our technical support team for a more detailed investigation.

Best regards,
[Your Name]
```

**Retrieved sources:** account_access_faq.md, troubleshooting_faq.md

**Missing fields:** account identifier, error message

**Reviewer** (review_id 7): APPROVED — follows as per the kb

</details>

<details>
<summary><strong>TCK-1008</strong> — Billing charge looks wrong (ESCALATE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out about the billing charge issue. To investigate this further, I would like to confirm your subscription plan and billing date, as per our troubleshooting guidelines [source: troubleshooting_faq.md]. 

Before proceeding, could you please provide one of the following to verify your account ownership: the registered email address, the account ID, or the most recent order ID, as outlined in our account access FAQ [source: account_access_faq.md]?

If the issue persists after verification, and you dispute the renewal charge, we may need to escalate this matter [source: subscription_policy.md] and follow the escalation guidance provided [source: subscription_policy.md] and [source: account_access_faq.md].

Please let me know how I can assist you further.

Recommended Action: If the customer's issue cannot be resolved after verifying the subscription plan and billing date, escalate the issue as it may involve a disputed renewal charge [source: subscription_policy.md].
```

**Retrieved sources:** account_access_faq.md, subscription_policy.md, troubleshooting_faq.md

**Missing fields:** account identifier, exact billing amount

**Reviewer** (review_id 8): APPROVED

</details>

<details>
<summary><strong>TCK-1009</strong> — You people are useless (REFUSE)</summary>

**Draft reply:**

```
I can't help with abusive or threatening requests.
```

**Retrieved sources:** abusive_content_policy.md, account_access_faq.md, troubleshooting_faq.md

**Missing fields:** issue description, account/order identifier

**Reviewer** (review_id 9): APPROVED

</details>

<details>
<summary><strong>TCK-1010</strong> — Refund abuse request (REFUSE)</summary>

**Draft reply:**

```
I can't assist with refund abuse or repeated refund requests outside the policy.
```

**Retrieved sources:** refund_policy.md

**Reviewer** (review_id 10): APPROVED

</details>

<details>
<summary><strong>TCK-1011</strong> — Refund exactly 7 days after purchase (AUTO_RESOLVE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us regarding your refund request for order ORD-4410. According to our refund policy [source: refund_policy.md], refund requests are accepted only within 7 days of the original purchase date. Since you are requesting a refund exactly 7 days after your purchase, your request is eligible for review under our standard policy [source: refund_policy.md].

We will proceed with reviewing your refund request. If there's any additional information needed from you, we will be in touch. Please allow us to process your request, and we will notify you of the outcome.

Thank you for your patience and cooperation.

Best regards,
Support Team
```

**Retrieved sources:** refund_policy.md

**Reviewer** (review_id 11): APPROVED

</details>

<details>
<summary><strong>TCK-1012</strong> — Want refund for recent purchase (ASK_INFO)</summary>

**Draft reply:**

```
Draft Reply:

To process your refund request, we need to verify your order details. As per our refund policy [source: refund_policy.md], to proceed with a refund review, we require the order ID or account email associated with the purchase. Could you please provide us with this information?

Once we have the necessary details, we can assess your eligibility for a refund based on our policy [source: refund_policy.md], which states that refund requests are accepted only within 7 days of the original purchase date.

If you have any further questions or concerns, please don't hesitate to reach out. We're here to assist you.

(Note: The customer's question about the refund is partially answered, but the specific eligibility for a refund cannot be determined without the order ID or account email. The response requests the necessary information to proceed with the refund review.)
```

**Retrieved sources:** refund_policy.md

**Missing fields:** order number

**Reviewer** (review_id 12): APPROVED

</details>

<details>
<summary><strong>TCK-1013</strong> — Something isn't working (ASK_INFO)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us about the issue you're experiencing. To better assist you, we need more information to diagnose the problem. According to our troubleshooting guidelines [source: troubleshooting_faq.md], it would be helpful to know the device or browser you're using, the date the issue started, the exact error message you're seeing, or your account identifier.

Could you please provide us with more details about the issue you're encountering? This will help us to provide a more accurate and efficient solution.

If we're unable to resolve the issue through standard troubleshooting steps, we may need to escalate the matter for further investigation [source: troubleshooting_faq.md].

Looking forward to hearing back from you with more information.

Best regards,
[Your Name]
```

**Retrieved sources:** account_access_faq.md, troubleshooting_faq.md

**Missing fields:** error description, symptoms

**Reviewer** (review_id 13): APPROVED

</details>

<details>
<summary><strong>TCK-1014</strong> — Cancel my plan (ASK_INFO)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

To cancel your plan, you can switch to a different plan or cancel your current subscription from the billing settings page [source: subscription_policy.md]. If you're unsure which plan you're currently on, you can check your account settings or billing history to confirm.

Please note that cancellation requests are effective at the end of the current billing period, unless otherwise stated by your account settings [source: subscription_policy.md]. Additionally, no refund is guaranteed for the current billing period [source: subscription_policy.md].

If you need assistance with locating your current plan or have questions about the cancellation process, I'd be happy to help. However, if you have any disputes or concerns about your billing or would like to request a special exception, I may need to escalate your issue [source: subscription_policy.md, source: refund_policy.md].

Best regards,
[Your Name]
```

**Retrieved sources:** refund_policy.md, subscription_policy.md

**Missing fields:** account identifier, plan details

**Reviewer** (review_id 14): APPROVED

</details>

<details>
<summary><strong>TCK-1015</strong> — Dispute annual renewal charge (ESCALATE)</summary>

**Draft reply:**

```
Draft Reply:

According to our subscription policy [source: subscription_policy.md], monthly and annual subscriptions renew automatically unless the customer cancels before the renewal date. It is stated that cancellation requests are effective at the end of the current billing period unless otherwise stated by the account settings. 

Since you are disputing a renewal charge, this issue falls under our escalation guidance [source: subscription_policy.md]. We recommend escalating this matter to further investigate and resolve the dispute regarding your annual renewal charge for subscription SUB-8823. 

Please allow us to escalate this issue to the relevant team for further assistance.
```

**Retrieved sources:** refund_policy.md, subscription_policy.md

**Reviewer** (review_id 15): APPROVED

</details>

<details>
<summary><strong>TCK-1016</strong> — Switch to monthly plan (AUTO_RESOLVE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

You can switch your subscription plan at any time from the billing settings page [source: subscription_policy.md]. To change your plan from annual to monthly billing for subscription SUB-5567, please navigate to the billing settings page and make the necessary adjustments. Please note that plan changes take effect at the next billing cycle [source: subscription_policy.md].

If you have any further questions or need assistance with this process, please let us know.

Best regards,
[Your Name]
```

**Retrieved sources:** subscription_policy.md, troubleshooting_faq.md

**Reviewer** (review_id 16): APPROVED

</details>

<details>
<summary><strong>TCK-1017</strong> — GDPR data export request (ESCALATE)</summary>

**Draft reply:**

```
Draft Reply:

Regarding your request for a complete copy of your personal data under GDPR, the provided context does not specify the process or details for handling such requests. Additionally, the data retention policy is not mentioned in the available documents [source: account_access_faq.md, source: refund_policy.md, source: troubleshooting_faq.md]. 

As the relevant policy could not be verified, we recommend escalating this matter to our support team for further assistance. They will be able to provide you with the necessary information and guidance on how to proceed with your GDPR data export request.
```

**Retrieved sources:** account_access_faq.md, refund_policy.md, troubleshooting_faq.md

**Reviewer** (review_id 71): APPROVED — since there is no policy we should escalate

</details>

<details>
<summary><strong>TCK-1018</strong> — Enterprise SSO integration (ESCALATE)</summary>

**Draft reply:**

```
Draft Reply:

Regarding SAML-based single sign-on for enterprise accounts, the provided context does not mention this topic. Therefore, the relevant policy could not be verified [source: account_access_faq.md, source: subscription_policy.md]. 

As for the request for a dedicated account manager, the context does not address this issue either. The provided information focuses on account access, troubleshooting, and subscription plan changes, without mentioning dedicated account management services.

It is recommended to escalate this inquiry to support, as the context does not provide sufficient information to address the customer's questions about SAML-based single sign-on and dedicated account management [source: account_access_faq.md, source: subscription_policy.md].
```

**Retrieved sources:** account_access_faq.md, subscription_policy.md

**Reviewer** (review_id 18): APPROVED

</details>

<details>
<summary><strong>TCK-1019</strong> — Account locked after failed logins (AUTO_RESOLVE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us about your account issue. According to our account access FAQ [source: account_access_faq.md], if your account is locked after repeated failed login attempts, you should wait 15 minutes before trying to log in again.

Please try logging in again after the specified time. If you continue to experience issues, we may need to request additional information to assist you further, such as confirming your registered email address or the most recent order ID [source: account_access_faq.md].

If the problem persists, we may need to escalate the issue for further investigation [source: account_access_faq.md] and [source: troubleshooting_faq.md].

Best regards,
Support Team
```

**Retrieved sources:** account_access_faq.md, troubleshooting_faq.md

**Reviewer** (review_id 19): APPROVED

</details>

<details>
<summary><strong>TCK-1020</strong> — Suspicious login activity (ESCALATE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us about the suspicious login activity on your account (ACC-7742). To better assist you, we would like to confirm your account ownership. According to our account access FAQ [source: account_access_faq.md], if the account is suspected to be compromised, we should escalate the issue to support. 

Before escalating, we would like to request some additional information to help diagnose the issue, as per our troubleshooting FAQ [source: troubleshooting_faq.md]. Could you please provide us with the device or browser being used, the date the issue started, and the exact error message you are seeing?

If we cannot verify your account ownership or gather sufficient information, we will escalate the issue to our support team for further investigation, as guided by our escalation guidance [source: account_access_faq.md] and [source: troubleshooting_faq.md].

We appreciate your cooperation and look forward to resolving this matter.

Best regards,
Support Team
```

**Retrieved sources:** account_access_faq.md, troubleshooting_faq.md

**Reviewer** (review_id 20): APPROVED

</details>

<details>
<summary><strong>TCK-1021</strong> — This is ridiculous (REFUSE)</summary>

**Draft reply:**

```
I can't help with abusive or threatening requests.
```

**Retrieved sources:** abusive_content_policy.md, account_access_faq.md, troubleshooting_faq.md

**Missing fields:** issue description, account/order identifier

**Reviewer** (review_id 21): APPROVED

</details>

<details>
<summary><strong>TCK-1022</strong> — App not loading on Safari (AUTO_RESOLVE)</summary>

**Draft reply:**

```
Draft Reply:

Dear Customer,

Thank you for reaching out to us about the issue with the app not loading on Safari. According to our troubleshooting guidelines [source: troubleshooting_faq.md], if the app is not loading, we recommend refreshing the browser and checking the internet connection. Could you please try this and see if it resolves the issue?

Additionally, to better assist you, could you please provide more information about the issue, such as the exact error message you're seeing (if any) and the date the issue started [source: troubleshooting_faq.md]? This will help us diagnose the problem more effectively.

If the issue persists after trying the above steps, we may need to escalate this to our support team for further investigation [source: troubleshooting_faq.md]. 

Please let us know if there's any further information we can assist you with.

Best regards,
Support Team
```

**Retrieved sources:** abusive_content_policy.md, account_access_faq.md, troubleshooting_faq.md

**Reviewer** (review_id 22): APPROVED

</details>
