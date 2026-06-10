# Schedule Generator System – Version 2.0

## Overview

Schedule Generator System is a university exam scheduling system developed in Python.

The system generates valid exam schedules for selected study programs while respecting academic constraints, exam periods, unavailable dates, and course requirements.

Version 2.0 significantly extends Version 1.0 by introducing:

- Full graphical user interface (GUI)
- MVP architecture
- Persistent application state
- Editable exam periods
- Streaming schedule generation
- Disk-based schedule storage
- Multiprocessing support
- Interactive schedule navigation and export


## System Overview

![Output Screen](output_screen.png)
---

# Main Features

## Data Loading

![Data loading](data_loading.png)

The system allows loading:

- Courses file
- Exam periods file

Supported formats:

- TXT
- CSV

Users can:

- Replace existing data
- Append additional data
- Reload files without restarting the application

---

## Study Program Selection

![Program selection](program_selection.png)

Users may:

- Search study programs
- View available programs
- Select up to 5 programs
- Remove selected programs
- View all courses belonging to a selected program

---

## Exam Period Editor

![Period editor](period_editor.png)

Users may edit exam periods before schedule generation.

Supported operations:

- Change start date
- Change end date
- Mark unavailable days
- Remove unavailable days
- Save changes

Validation ensures that edited periods remain consistent.

---

## Schedule Generation

The system generates all valid schedules that satisfy:

- Academic constraints
- Program requirements
- Course conflicts
- Exam period limitations
- User-defined unavailable days

Generation is performed in the background while keeping the GUI responsive.

---

## Schedule Navigation

Users can:

- Browse generated schedules
- Move forward/backward between schedules
- Navigate independently per exam period
- Switch between semesters
- Switch between Moed A / B / C schedules

---

## Schedule Export

Users can export the currently selected schedules into a report file.

The export process:

1. Reads the selected schedule from each period.
2. Merges all selected schedules.
3. Generates a final report.

---

# Architecture

![MultiProcessArchitectureDiagram](image-4.png)

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

Dependencies flow in one direction only.

No View component directly accesses algorithmic classes.

---

# Layer Structure

## View Layer

Responsible for all GUI functionality.

Main components:

- MainWindow
- InputScreen
- OutputScreen
- Widgets
- Dialogs

---

## Presenter Layer

Acts as the mediator between GUI and business logic.

Main components:

- AppService
- DataStore
- EngineProcess
- EngineListener
- ResultsReader

---

## Algorithm Layer

Contains the scheduling engine.

Main components:

- SchedulingEngine
- BacktrackingSolver
- ConstraintValidator
- ForwardChecker
- ConstraintIndex

---

## Parsers Layer

Responsible for loading system data.

Main components:

- CourseParser
- ExamPeriodFileParser
- ProgramParser
- ProgramsNameParser

---

## Models Layer

Contains domain entities.

Main components:

- Course
- ExamPeriod
- ExamSchedule
- ProgramRequirement

---

# Singleton Design

Version 2.0 introduces a Singleton-based AppService.

Reasons:

- Centralized application state
- Shared DataStore
- Shared EngineProcess
- Consistent data across screens
- Simplified dependency injection

Only one AppService instance exists during application runtime.

---

# Multiprocessing Architecture

## Motivation

Python's Global Interpreter Lock (GIL) limits true CPU parallelism for threads.

Running the scheduling engine inside the GUI process could freeze the interface while generating schedules.

---

## Solution

The scheduling engine runs inside a separate operating-system process.

```text
GUI Process
    │
    ├── task_queue
    │
Scheduling Process
    │
    └── notify_queue
```

Communication is performed through multiprocessing queues.


### task_queue

Used to send generation requests from the GUI to the scheduling engine.

### notify_queue

Used to send status updates and completion notifications back to the GUI.

The scheduling process remains alive throughout the application's lifecycle and can handle multiple generation requests without being recreated.

Benefits:

- Responsive GUI
- Better CPU utilization
- Process isolation
- Safe background computation
- Reusable scheduling process

---

# Streaming Schedule Generation

## Problem in Version 1.0

The algorithm returned results only after completing the entire search.

Consequences:

- Long waiting times
- Large memory consumption

---

## Solution

Version 2.0 introduces Generator-based schedule generation.

Main methods:

```python
solve_stream()
_backtrack_stream()
```

Schedules are yielded one-by-one:

```python
yield schedule
```

Benefits:

- Immediate result availability
- Reduced memory consumption
- Ability to stop generation at any time

---

# Disk-Based Storage

## Problem

Keeping all schedules in RAM becomes impractical when thousands of schedules are generated.

---

## Solution

Schedules are written directly to disk.

Components:

### PeriodResultsWriter

Stores schedules in batches.

Files:

```text
batch_0000.pkl
batch_0001.pkl
...
```

Maintains:

```text
manifest.json
```

### Manifest File

Each period directory contains a manifest.json file.

The manifest stores metadata about the generated schedules, including:

- Total number of schedules
- Number of batch files
- Batch indexing information

This allows the application to locate schedules efficiently without scanning every batch file on disk.

---

### ResultsReader

Loads only the required schedule when needed.

Benefits:

- Constant memory usage
- Fast retrieval
- Scalability

---

# GUI Screens

## Input Screen

The input screen allows:

- Loading files
- Selecting study programs
- Viewing program courses
- Editing exam periods
- Starting schedule generation

Main widgets:

- FileLoaderWidget
- ProgramListWidget
- SelectedProgramsPanel
- CourseTableWidget
- PeriodListWidget
- PeriodEditorWidget

---

## Output Screen

The output screen allows:

- Viewing generated schedules
- Navigating schedules
- Viewing exam details
- Downloading schedules

Main widgets:

- ScheduleNavigatorWidget
- SemesterTabsWidget
- MoedCalendarOutputWidget
- DayDetailDialog

---

# Data Persistence

Application state is stored using:

```text
DataStore
```

Stored information:

- Loaded courses
- Exam periods
- Program names
- Selected programs

The state survives screen transitions.

---

# UML Diagrams

The project includes UML diagrams under:

```text
docs/UML/
```

The original diagrams from Version 1.0 were preserved and updated where necessary.

In addition, Version 2.0 introduces new UML diagrams documenting the new architecture and GUI components.

## Version 1.0 Diagrams

- AlgorithmDiagram
- AppControllerDiagram
- ParsersDiagram

## Version 2.0 Diagrams

- AlgorithmDiagramV2
- ParsersDiagramV2
- InputScreenDiagram
- OutputScreenDiagram
- PresenterLayerClassDiagram
- ViewLayerClassDiagram
- MultiProcessArchitectureDiagram


## Available Formats

For each diagram the repository contains:

- PNG exports
- Mermaid (.mmd) source files
- Markdown documentation (.md)

These diagrams document:

- System architecture
- MVP layer separation
- Input screen structure
- Output screen structure
- Multiprocessing communication model
- Presenter layer responsibilities
- View layer organization
- Parsing subsystem
- Scheduling subsystem


# Documentation

The project documentation can be found under:

docs/

Contents include:

- UML diagrams
- Architecture documentation
- Mermaid source files
- Design documentation for Version 2.0

The documentation was expanded significantly in Version 2.0 to reflect the new GUI architecture, multiprocessing infrastructure, and presenter layer design.

---

# Project Structure

```text
Project-SE-year-2
│
├── data
├── docs
├── icon
├── src
│   ├── algorithm
│   ├── models
│   ├── output
│   ├── parsers
│   ├── presenter
│   ├── styles
│   └── views
│
├── tests
├── README.md
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

# Installation

## Requirements

- Python 3.10+
- pip

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Application

From the project root:

```bash
python -m src.main
```

The application will launch the graphical user interface.

---

# Running Tests

Run all tests:

```bash
pytest
```

Verbose mode:

```bash
pytest -v
```

Specific file:

```bash
pytest tests/test_file_name.py
```

---

# Technologies Used

- Python
- PyQt5
- Multiprocessing
- Threading
- Pickle
- JSON
- Pytest

---

# Version Comparison

## Version 1.0

- Command-line oriented workflow
- In-memory result storage
- Sequential generation
- No GUI
- No persistence

---

## Version 2.0

- Full GUI
- MVP architecture
- Singleton AppService
- Multiprocessing engine
- Generator streaming
- Disk-based storage
- Editable exam periods
- Schedule navigation
- Schedule export
- Persistent application state

---

## Known Limitations

> ⚠️ UI Scaling Limitation
>
> The current version was primarily tested on standard desktop resolutions.
> On some screen sizes or display scaling configurations, certain widgets may
> appear partially hidden or inaccessible. This issue is planned to be resolved
> in the next milestone.

---