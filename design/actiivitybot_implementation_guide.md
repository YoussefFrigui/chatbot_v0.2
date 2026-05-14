# Implementation Guide: Activity chatbot Workbench

This document provides the structural and stylistic requirements for an AI agent to implement the Activity chatbot interface.


## Visual Identity
The design follows the **Technical Precision** design system:
- **Primary Color**: `#ec4899` (used for CTAs, active states, and accents)
- **Background**: `#051424` (Deep navy surface)
- **Typography**: Geist (Sans-serif, monospace for technical data)
- **Shape**: 4px border radius for components

## Layout Structure
1.  **Global Navigation (TopBar)**: 56px height. Contains the brand logo ("Activity Chatbot"), primary nav links, and utility icons (Settings, Help, Account).
2.  **Side Navigation**: Vertical sidebar for project-level navigation (Workbench, Models, Knowledge, Evaluation) and model selection toggles.
3.  **Comparison Workspace**: Dynamic flex/grid container that scales based on the number of active models. Each model response is contained in a separate column with its own header (Latency/Status).
4.  **Evaluation Sidebar (Right)**: Fixed width (approx. 320px). Displays:
    - **Ground Truth**: Reference text for RAG evaluation.
    - **RAGAS Metrics**: Progress bar-style visualizations for Faithfulness, Relevance, and Precision.
    - **Model Delta Table**: Statistical comparison (BLEU, ROUGE-L, METEOR).
5.  **Input Area (Bottom)**: Multi-line text area with attachment capability and a prominent primary action button.

## Key Interaction Patterns
- **Model Selection**: Toggling a checkbox in the sidebar should dynamically add/remove columns in the comparison workspace.
- **Run Batch**: Primary action in the sub-header to execute the same prompt across all selected models.
- **Citations**: Highlighted references within model responses that link to sources.