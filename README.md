# 🍲 Donate Nearby

> **Turning surplus event food into meals for those who need it — in real time.**

A direct, real-time platform connecting event organizers with nearby verified NGOs to rescue leftover food from weddings, parties, fests, and corporate events before it spoils.

Built by **Team GENSQUAD** for the **Ignition Hackathon Series**.

---

## 📌 The Problem

* **Events Over-Prepare:** Weddings, college fests, and corporate functions routinely cook far more food than gets eaten.
* **No Time to Act:** Organizers have a narrow window of hours before cooked food is no longer safe to consume.
* **No Quick NGO Contact:** Finding and coordinating with available NGOs nearby on short notice is difficult and slow.
* **Result:** Tons of good, edible food ends up in the trash while vulnerable communities go hungry.

---

## 💡 Our Solution

**Donate Nearby** provides a real-time bridge between event hosts and nearby non-profits:
* Organizers list surplus food with pickup details in seconds.
* The platform calculates geodesic distance using the **Haversine Formula** to find the closest NGOs first.
* NGOs receive instant alerts and can claim/accept pickups with a single tap from their dashboard.

---

## 🚀 Key Features

* 📝 **Post Surplus Food:** Simple form for organizers to list quantity, food type, pickup location, dietary category, and safe-until expiry time[cite: 1].
* 📍 **Location-Based Matching:** Uses browser geolocation and the **Haversine formula** to calculate precise distances to local NGOs[cite: 1].
* ⚡ **Live Auto-Refreshing Dashboards:** Built-in polling mechanism keeps listings and claim statuses synced in real time without heavy paid infrastructure[cite: 1].
* ✅ **One-Tap Pickup Claiming:** NGOs can view details on interactive maps/lists and accept pickups directly[cite: 1].
* 🛡️ **Secure Authentication:** Password hashing powered by Werkzeug Security for both organizer and NGO accounts[cite: 1].
* 📊 **Status Tracking:** End-to-end lifecycle management (*Pending* ➔ *Accepted* ➔ *Completed/Picked Up*)[cite: 1].

---

## 🔄 How It Works

```text
  [ 1. Post Food ]  ──▶  Organizer lists surplus food & pickup details.[cite: 1]
         │
         ▼
 [ 2. Match Nearby ] ──▶  App calculates distances using Haversine algorithm.[cite: 1]
         │
         ▼
  [ 3. NGO Accepts ] ──▶  Nearest NGO receives alert and accepts the pickup.[cite: 1]
         │
         ▼
[ 4. Food Delivered ] ──▶  Surplus food is safely collected and distributed.[cite: 1]
