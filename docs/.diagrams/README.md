# Algorithm Diagrams

This folder contains PlantUML source files and their rendered images for the Quran AI verse matching algorithm.

## Structure

```
.diagrams/
├── src/                          # PlantUML source files (.puml)
│   ├── constraint-propagation.puml
│   ├── backward-gap-filling.puml
│   ├── forward-consecutive-matching.puml
│   └── complete-flow.puml
├── images/                       # Rendered PNG/SVG images
│   ├── constraint-propagation.png
│   ├── backward-gap-filling.png
│   ├── forward-consecutive-matching.png
│   └── complete-flow.png
└── README.md                     # This file
```

## Diagrams

### 1. Constraint Propagation Algorithm
**File:** `src/constraint-propagation.puml`

Shows how the algorithm analyzes multiple word batches and intersects results to identify the correct surah and starting ayah.

### 2. Backward Gap Filling
**File:** `src/backward-gap-filling.puml`

Illustrates the process of filling missing ayahs before the constraint-propagated start ayah.

### 3. Forward Consecutive Matching
**File:** `src/forward-consecutive-matching.puml`

Demonstrates how the algorithm matches consecutive verses forward with miss tolerance.

### 4. Complete Algorithm Flow
**File:** `src/complete-flow.puml`

End-to-end flow from audio input to verse-matched output, showing all components.

## Rendering Diagrams

### Option 1: VSCode Extension
1. Install the PlantUML extension
2. Open any `.puml` file
3. Press `Alt+D` to preview

### Option 2: Command Line
```bash
# Install PlantUML
sudo apt-get install plantuml

# Render a diagram
plantuml src/constraint-propagation.puml -o ../images/

# Render all diagrams
plantuml src/*.puml -o ../images/
```

### Option 3: Online
Visit http://www.plantuml.com/plantuml/uml/ and paste the content

### Option 4: Docker
```bash
docker run -v $(pwd):/data plantuml/plantuml -tpng /data/src/*.puml -o /data/images/
```

## Updating Diagrams

1. Edit the `.puml` file in `src/`
2. Render to `images/` folder
3. Update references in `../ALGORITHM.md`
4. Commit both source and rendered images

## Image Formats

- **PNG:** For documentation (default)
- **SVG:** For scalable web display
- **PDF:** For print documentation

To generate different formats:
```bash
plantuml -tpng src/*.puml -o ../images/   # PNG
plantuml -tsvg src/*.puml -o ../images/   # SVG
plantuml -tpdf src/*.puml -o ../images/   # PDF
```

## References

- PlantUML Documentation: https://plantuml.com/
- PlantUML Activity Diagram: https://plantuml.com/activity-diagram-beta
- Online Editor: http://www.plantuml.com/plantuml/uml/
