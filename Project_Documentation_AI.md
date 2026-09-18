# Artificial Intelligence Project Documentation
**Project Title:** Schoole-AI: Intelligent Academic Assistant & Decision System  
**Instructor:** T. Alwaleed Alduais  

---

## 1. Problem Description
Schools and educational institutions face overwhelming volumes of repetitive inquiries from students and parents regarding schedules, curriculum, exams, and teacher assignments. Managing these inquiries manually consumes significant administrative time. Furthermore, optimizing school operations, such as identifying the minimum number of teachers required to cover specific subject combinations, is a complex scheduling problem. 
**Our solution** is an intelligent assistant (Expert System & Chatbot) that automates information retrieval, answers inquiries autonomously, and incorporates an optimization algorithm for decision-making.

## 2. AI Technique Selection
The system implements a **Hybrid AI approach**, combining multiple techniques covered in the course:
1. **Natural Language Processing (NLP) & Inference Engine:** Utilized for building the Intelligent Assistant. The system uses Fuzzy String Matching, Tokenization, and Intent Routing to understand Arabic queries and retrieve correct responses.
2. **Knowledge Representation (Knowledge-Based System):** The domain knowledge is explicitly represented using structured JSON Knowledge Bases (Ontologies) separated by domain (Curriculum, FAQ, Teachers, Schedules).
3. **Search & Optimization (Greedy Algorithm):** Implemented to solve the "Set Cover Problem". The system intelligently recommends the minimum number of teachers required to cover a selected set of subjects by making locally optimal greedy choices.

## 3. System Architecture
The project strictly separates the AI component from the application layer to maintain scalability. **(Bonus criteria achieved: Independent REST API).**

*   **User Interface (Frontend):** HTML, CSS, JavaScript (Vanilla). Includes a modern chat interface, Voice AI (Speech-to-Text/Text-to-Speech), and an Administrator Analytics Dashboard.
*   **Application Layer:** Built using the **Django** Python Framework. It routes web traffic and serves static files.
*   **AI Engine (Independent REST API):** The `InferenceEngine` class operates as an independent backend service. It receives raw text via a JSON POST request (`/api/chat/`), processes the AI logic, and returns a JSON response.
*   **Knowledge Base:** A collection of JSON files acting as the system's brain (`faq.json`, `curriculum_books.json`, etc.).
*   **Database:** SQLite3 is used solely for logging interactions (`ChatLog`) and user evaluations (`Feedback`) to measure AI performance.

## 4. Knowledge Base Description
The system avoids traditional relational databases for AI reasoning. Instead, it relies on hierarchical JSON structures. For instance, the Knowledge Base categorizes educational stages, mapping grades to specific subjects, teachers, and textbooks. The engine parses this data into memory at runtime to form a traversable rule set.

## 5. Algorithm Design & Flow
**A. NLP Inference Flow:**
1. User submits query (Text or Voice).
2. Engine normalizes text (removes punctuation, unifies Arabic characters).
3. **Intent Detection:** The system checks against predefined heuristic rules (e.g., if keywords match "timetable", route to `_handle_schedule`).
4. **Fuzzy Deep Search:** If no exact intent matches, the algorithm traverses the entire JSON Knowledge Base, calculating a similarity score for each node, and returns the highest-scoring node's content.

**B. Greedy Optimization Flow (Teacher Assignment):**
1. Identify all uncovered requested subjects.
2. Iterate over available teachers to find who covers the maximum number of currently uncovered subjects.
3. Make the **Greedy Choice**: Select that teacher and remove their subjects from the uncovered list.
4. Repeat until all subjects are covered.

## 6. AI Decision Process & Explainability (White-Box AI)
To avoid the "Black-Box" dilemma, the system provides full transparency for its decisions:
*   **Confidence Score & Metadata:** Every response rendered in the UI is accompanied by a metadata pill showing the `Detected Intent`, `Data Source File`, and `Confidence Score %`.
*   **Reasoning Explanation:** When the Greedy Algorithm runs, it outputs a step-by-step "Thinking Log" (e.g., *"Step 1: Selected Teacher X because they cover 3 remaining subjects"*).

## 7. AI Evaluation Results
The system implements a continuous **Human-AI Interaction Feedback Loop**. Users can rate responses (👍/👎). The administration dashboard tracks these metrics:
*   **Execution Time:** Average response time is calculated and logged (typically < 100ms).
*   **Decision Accuracy / Satisfaction:** Monitored via the Dashboard's "Satisfaction Rate" (Positive Feedbacks / Total Feedbacks).
*   **Intent Accuracy:** The dashboard charts the most frequently triggered intents, allowing developers to see where the NLP engine excels or fails.

## 8. Human-AI Interaction & Innovation
*   **Voice Integration (Accessibility):** Users can interact completely hands-free using the Web Speech API (Speech-to-Text and Text-to-Speech).
*   **Interactive Chat UI:** Typing indicators, smart chip suggestions, and real-time response rendering simulate human conversation.

## 9. Limitations
*   The NLP engine currently relies heavily on keyword extraction and fuzzy matching, which may fail to understand deep semantic meaning (sarcasm or highly complex phrasing) compared to large language models (LLMs).
*   The Greedy Algorithm provides a highly efficient approximation but does not guarantee the absolute optimal mathematical solution in extreme edge cases (inherent limitation of Greedy algorithms).

## 10. Future Improvements
*   Integrating a Machine Learning classification model (e.g., Support Vector Machine or Neural Network) for more robust intent detection.
*   Expanding the Knowledge Base to cover predictive models for student attendance or grade forecasting.
