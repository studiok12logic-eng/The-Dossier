# The-Dossier
人間をハックし、信頼を構築せよ。

# PROJECT SPECIFICATION: TERESA::CONNECTED_DB

## 1. Project Overview & Philosophy
**System Name:** The-Dossier
**Framework:** Django (Python)
**Concept:** "Underground Command Center" for Interpersonal Intelligence.

> **Mission Statement**
> # "Hack the Human, Build the Rapport."
> **人間をハックし、信頼を構築せよ。**

### Core Value
This is not just a CRM. It is a strategic interface to gamify social interactions.
* **Objective:** Transform vague conversations into "Quests" and visualize "Intel Depth" (Rapport level).
* **Atmosphere:** Noir, Cyberpunk, Intelligence Agency style.
* **Role:**
    * User = **"Handler"** (Controller)
    * Target = **"Subject"** (Person of Interest)
    * System = **"Intelligence Officer"** (Navigator)

---

## 2. Functional Requirements

### 2.1. Target Management (Core)
* **Registration**: 
    * Name, Nickname (Mandatory), Birthdate (Split fields Y/M/D), Gender, Blood Type, Origin.
    * **Auto-Calculation**: Age (Traditional/Modern), Zodiac Sign.
    * **Image Processing**: Upload -> Crop (300x300) -> Apply "Grayscale + Noise" filter automatically.
* **Views**:
    * **Icon View**: Minimal grid (Img, Name, Rank).
    * **Card View**: Detailed grid (Img, Name, Rank, Last Contact, One-line Memo).

### 2.2. Dossier & Timeline (Detail View)
A unified timeline interface resembling a chat app, split into two modes:
1.  **Event Mode (Observation Log)**
    * Log daily interactions (Dining, Habits, Fashion).
    * Tagging system (e.g., `#Gift`, `#Taboo`, `#Alcohol`).
    * Full-text search support.
2.  **Quest Mode (Interrogation Log)**
    * Answer specific questions provided by the system.
    * Progress tracking based on answered quests per category.

### 2.3. Quest System
* **Global Quest Master**: Manage questions like "What is their childhood dream?", "Favorite movie?".
* **Cross-Reference**: View all subjects' answers for a specific quest to identify intelligence gaps.

---

## 3. Database Schema (Django Models)

The database must be designed to accommodate the imported CSV data structure while maintaining relational integrity.

### 3.1. `Core` App (Accounts & System)
* **User**: Extended AbstractUser. Represents the "Handler".

### 3.2. `Intelligence` App (Main Logic)

#### Model: `Target` (Subject of Investigation)
* **id**: UUID
* **last_name**: CharField
* **first_name**: CharField
* **nickname**: CharField (Required, Display Name)
* **rank**: ChoiceField (S, A, B, C, Taboo, System)
    * *Note: 'System' rank is for Teresa (AI).*
* **birth_year**: IntegerField (Nullable)
* **birth_month**: IntegerField
* **birth_day**: IntegerField
* **gender**: ChoiceField
* **blood_type**: ChoiceField
* **origin**: CharField (Place of birth/growth)
* **avatar**: ImageField (Stores processed noisy image)
* **intel_depth**: FloatField (Calculated score 0-100%)
* **last_contact**: DateTimeField
* **memo**: TextField (One-line summary)
* **created_at**: DateTime

#### Model: `CustomAnniversary`
* **target**: ForeignKey(Target)
* **label**: CharField (e.g., "First Meeting", "Surgery Date")
* **date**: DateField

#### Model: `Quest` (The Question Master)
* **text**: CharField (e.g., "好きな映画は？")
* **category**: CharField (Work, Love, Past, Taboo, Values)
* **difficulty**: IntegerField (1-5)

#### Model: `TimelineItem` (Unified Log)
* **target**: ForeignKey(Target)
* **type**: ChoiceField (EVENT, ANSWER)
* **date**: DateTimeField
* **content**: TextField
    * *If type=EVENT: Stores the observation text.*
    * *If type=ANSWER: Stores the answer to the linked Quest.*
* **related_quest**: ForeignKey(Quest, Nullable)
* **tags**: ManyToManyField('Tag')
* **sentiment**: ChoiceField (Positive, Neutral, Negative, Alert)

#### Model: `Tag`
* **name**: CharField (e.g., "Gift", "Dinner", "Conflict")

---

## 4. UI/UX Design Guidelines

### 4.1. Color Palette (Tailwind CSS variables)
* **Primary (Accent)**: `#10b981` (Emerald-500) - Represents "Data Integrity" & "Bio-signal".
* **Background**: `#050505` (Deep Black) - Represents "The Void" & "Underground".
* **Surface**: `#0f1110` (Dark Gray) - Card backgrounds.
* **Text**: `#ecfdf5` (Mint White) - High contrast terminal text.

### 4.2. Visual Effects
* **The "Noise" Protocol**: 
    * All user avatars MUST undergo a CSS filter or server-side processing: `grayscale(100%) contrast(120%) noise-overlay`.
    * This unifies the look of disparate photos into a coherent "Database" aesthetic.
* **Typography**:
    * Headers/Data: Monospaced fonts (Courier New, Roboto Mono).
    * Body: Clean Sans-serif (Inter, Helvetica).

### 4.3. Navigation Structure
1.  **Dashboard**: Stats overview.
2.  **Target List**: Grid view of Targets with search/filter.
3.  **Quest Board**: Kanban or List view of unanswered quests.
4.  **Settings**: User profile & System configs.
