# Schedule Generator System – Version 3.0

This repository contains the final implementation developed during Milestone 3.

Documentation for Milestone 1 is available under:
[docs/Milestone1/README_Milestone_1.md](docs/Milestone1/README_Milestone_1.md)

## Overview

Schedule Generator System is a university exam scheduling system developed in Python.

The system generates valid exam schedules for selected study programs while respecting academic constraints, exam periods, unavailable dates, and course requirements.

Version 3.0 significantly extends previous versions by introducing:
- Full graphical user interface (GUI)
- Advanced Filters and Sorting capabilities (New!)
- Room Schedules generation (New!)
- Interactive Schedule Editing & Regeneration (New!)
- Editable exam periods & Banned days highlighting
- MVP architecture
- Persistent application state
- Streaming schedule generation
- Disk-based schedule storage
- Multiprocessing support
- Interactive schedule navigation and export

---

## Visual Walkthrough & Features

### 1. Main Application Screen
![Entering Screen](data/App%20Screenshots/entering%20screen.png)
The initial view allows you to load files, select study programs, and configure the basic details before running the generator.

### 2. Constraints & Input Settings
![Input Settings](data/App%20Screenshots/input%20settings.png)
Configure mandatory gaps, filters, and other scheduling constraints directly from the settings panel.

### 3. Study Program Selection
![After Choosing a Program](data/App%20Screenshots/after%20choosing%20a%20program.png)
Search and select up to 5 study programs. You can view all courses belonging to a selected program and remove them if needed.

### 4. Editing Exam Periods
![Editing Periods](data/App%20Screenshots/editing%20periods.png)
Edit exam periods before schedule generation. Change start/end dates, and mark unavailable (banned) days which are clearly highlighted in the calendar.

### 5. Sorting & Ranking Settings
![Sorting Settings](data/App%20Screenshots/sorting%20settings.png)
Customize how the generated schedules are ranked and sorted based on various weighting factors to prioritize the most optimal schedules, paired with our new advanced filtering options.

### 6. Results & Schedule Output
![Second Screen](data/App%20Screenshots/second%20screen.png)
The output screen displays all generated schedules. Browse through options, interactively edit the schedule, regenerate specific parts, view room schedules, and export the final report.

---

<details>
<summary><b>🤓 For the Geeks: Technical Architecture & Flow Explanations</b></summary>

## System Architecture

The project follows the MVP (Model–View–Presenter) architectural pattern.

```text
View
 ↓
Presenter
 ↓
Algorithm
 ↓
Models
```

Dependencies flow in one direction only. No View component directly accesses algorithmic classes.

### Layer Structure

#### View Layer
Responsible for all GUI functionality.
- MainWindow, InputScreen, OutputScreen, Widgets, Dialogs

#### Presenter Layer
Acts as the mediator between GUI and business logic.
- AppService, DataStore, EngineProcess, EngineListener, ResultsReader

#### Algorithm Layer
Contains the scheduling engine.
- SchedulingEngine, BacktrackingSolver, ConstraintValidator, ForwardChecker, ConstraintIndex

#### Parsers Layer
Responsible for loading system data.
- CourseParser, ExamPeriodFileParser, ProgramParser, ProgramsNameParser

#### Models Layer
Contains domain entities.
- Course, ExamPeriod, ExamSchedule, ProgramRequirement, Room

### Singleton Design
The application utilizes a Singleton-based AppService to centralize application state, share the DataStore and EngineProcess, keep consistent data across screens, and simplify dependency injection. Only one AppService instance exists during runtime.

### Multiprocessing Architecture

**Motivation:** Python's Global Interpreter Lock (GIL) limits true CPU parallelism for threads. Running the engine inside the GUI process could freeze the interface.

**Solution:** The scheduling engine runs inside a separate OS process.
```text
GUI Process
    │
    ├── task_queue
    │
Scheduling Process
    │
    └── notify_queue
```
Communication is via multiprocessing queues (`task_queue`, `notify_queue`).

### Streaming Schedule Generation

**Problem in older versions:** Algorithm returned results only after completing the entire search, leading to long waiting times and large memory consumption.

**Solution:** Generator-based schedule generation.
```python
solve_stream()
_backtrack_stream()
```
Schedules are yielded one-by-one (`yield schedule`), resulting in immediate availability, reduced memory consumption, and the ability to stop at any time.

### Disk-Based Storage

**Problem:** Keeping thousands of schedules in RAM is impractical.

**Solution:** Schedules are written directly to disk.
- **PeriodResultsWriter:** Stores schedules in batches (`batch_0000.pkl`, `batch_0001.pkl`...) and maintains a `manifest.json`.
- **Manifest File:** Stores metadata (total schedules, batch indexing) allowing efficient location without scanning every file.
- **ResultsReader:** Loads only required schedules when needed, ensuring constant memory usage and fast retrieval.

### UML Diagrams

The project includes UML diagrams under: `docs/UML/`

These diagrams document:
- System architecture
- MVP layer separation
- Input/Output screen structure
- Multiprocessing communication model
- Presenter layer responsibilities
- View layer organization
- Parsing/Scheduling subsystems
</details>

---

# Installation

## Requirements
- Python 3.10+
- pip

## Install Dependencies
```bash
pip install -r requirements.txt
```

# Running the Application
From the project root:
```bash
python -m src.main
```
The application will launch the graphical user interface.

# Running Tests
Run all tests:
```bash
pytest
```
Verbose mode:
```bash
pytest -v
```

# Technologies Used
- Python
- PyQt5
- Multiprocessing
- Threading
- Pickle
- JSON
- Pytest

# Known Limitations
> ⚠️ UI Scaling Limitation
>
> The current version was primarily tested on standard desktop resolutions.
> On some screen sizes or display scaling configurations, certain widgets may
> appear partially hidden or inaccessible. This issue is planned to be resolved
> in future updates.