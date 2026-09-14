# PRD Agent — Example

**Client**: "We want an app where people can book appointments with local tutors."

**Agent**: Who books — students directly, or parents booking for kids?

**Client**: Mostly parents, for K-12. Some adult learners book for themselves.

**Agent**: What's broken with how they do this today — phone calls, spreadsheets, a competitor app?

**Client**: Word of mouth and WhatsApp groups. No visibility into tutor availability, no way to pay online.

**Agent**: What does success look like six months in — more tutors signed up, more bookings, revenue?

**Client**: Revenue via a booking fee, and we want 100 active tutors in the first market.

**Agent**: For v1, does a tutor need their own calendar sync (Google/Outlook), or is manual availability entry enough?

**Client**: Manual is fine for v1.

**Agent**: Payment — are you handling this yourselves or through a processor like Stripe?

**Client**: Stripe, we already have an account.

**Agent**: Any compliance concerns given this touches minors — parental consent, data handling for K-12 students?

**Client**: Yes, we need parental consent captured before a minor's profile is created.

**Agent**: Deadline or budget constraint I should know about?

**Client**: Want to launch in 3 months, budget for one dev team.

**Agent**: Here's what I've got — confirm before I write it up:
- Parents (mostly) and adult learners book appointments with local tutors
- Tutors set manual availability (no calendar sync in v1)
- Stripe handles payment, platform takes a booking fee
- Parental consent required before a minor's profile is created
- Goal: 100 active tutors in first market within 6 months
- 3-month timeline, one dev team

Sound right?

**Client**: Yes, one more thing — tutors need to set their own hourly rate.

**Agent**: Got it, adding that. Writing the PRD now.

---

## Output

```
# PRD: Local Tutor Booking Platform

## Problem Statement
Parents and adult learners currently find and book local tutors through word of mouth
and informal WhatsApp groups, with no visibility into availability and no online payment.

## Goals
- Launch a booking platform connecting parents/students with local tutors
- Reach 100 active tutors in the first market within 6 months
- Generate revenue via a per-booking fee

## Non-Goals
- Calendar sync (Google/Outlook) for tutors — manual availability only in v1
- Multi-market launch — single market first

## Target Users
- Parent: books and pays for a tutor on behalf of a K-12 child
- Adult learner: books and pays for their own sessions
- Tutor: lists profile, sets availability and hourly rate, gets booked and paid

## Requirements
### Must Have (v1)
- [ ] Tutor profile with bio, subjects, hourly rate
- [ ] Manual availability entry by tutor
- [ ] Search/browse tutors by subject and availability
- [ ] Booking flow with Stripe payment (booking fee applied)
- [ ] Parental consent flow required before a minor's student profile is created

### Should Have
- [ ] Ratings/reviews after a session

### Could Have (later)
- [ ] Calendar sync for tutors
- [ ] Multi-market support

## Constraints
- 3-month timeline, single dev team
- Stripe as the only payment processor
- Parental consent required for minors (compliance)

## Success Metrics
- 100 active tutors in first market within 6 months
- Booking completion rate, revenue per booking

## Open Questions
- Refund/cancellation policy — not yet defined, owner: client
- Tutor vetting/background checks — not yet defined, owner: client
```
