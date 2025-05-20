# 5. Configure the Scoring Engine

## 5a. Initial Display

### Display:
- A heading: "Configure Scoring Engine".
- Help text explaining the purpose of the Scoring Engine. Explain that depending on whether a PyRIT-based or Garak-based pipeline was selected in Section 2, you'll configure either Scorers (for PyRIT) or Detectors (for Garak). Scorers and Detectors are tools that evaluate the Generator's outputs to determine factors like whether a response is harmful, contains code, or fails to comply with policies.

### Backend:
- Determine the pipeline type configured in Section 2:
  - If **PyRIT-based pipeline**, display options for Scorers.
  - If **Garak-based pipeline**, display options for Detectors.

## 5b. Add Scorer Flow

This is a repeating flow triggered by the "Add Scorer" button.

### 5b.1 Select Scorer or Detector Type

#### For PyRIT-based pipeline:

### Display:
- `st.selectbox` labeled "Select Scorer Type".

### Action:
- User selects a scorer type.

### Backend:
- Store the selected scorer class in `st.session_state["current_scorer_class"]`.

#### For Garak-based pipeline:

### Display:
- `st.selectbox` labeled "Select Detector Type".

### Action:
- User selects a detector type.

### Backend:
- Store the selected detector class in `st.session_state["current_detector_class"]`.

### 5b.2 Configure Scorer or Detector Parameters (Dynamic)

#### For PyRIT-based pipeline (Scorers):

### Display:
- Provide input fields based on the selected scorer, including required and optional parameters.

### Action:
- User fills in the parameters.

### Backend:
- Validate inputs and store them in `st.session_state["current_scorer_params"]`.

#### For Garak-based pipeline (Detectors):

### Display:
- Provide input fields based on the selected detector, including required and optional parameters.

### Action:
- User fills in the parameters.

### Backend:
- Validate inputs and store them in `st.session_state["current_detector_params"]`.

### 5b.3 Add Scorer or Detector

### Display:
- An "Add Scorer" or "Add Detector" button.

### Action:
- On clicking "Add", the system saves the configuration.

### Backend:
- For PyRIT scorers, update the parameter file with the scorer details.
- For Garak detectors, update the parameter file with the detector details.

### 5b.4 Display Configured Scorers or Detectors

### Display:
- A list showing each configured scorer or detector, including:
  - "Remove" and "Test" buttons for each scorer or detector.

### Action:
- User can remove a scorer or detector.
- User can test a scorer or detector.

### Backend:
- For removal, update the session state and parameter files accordingly.

### 5b.5 Test a Configured Scorer or Detector

#### For PyRIT-based pipeline (Scorers):

### Display:
- A section titled "Test a Configured Scorer".
- A "Run Test" button.

### Action:
- User selects a scorer, provides test input, clicks "Run Test".

### Backend:
- When "Run Test" is clicked, execute the scorer on the test input and display results.

#### For Garak-based pipeline (Detectors):

### Display:
- A section titled "Test a Configured Detector".
- A "Run Test" button.

### Action:
- User selects a detector, provides test input, clicks "Run Test".

### Backend:
- When "Run Test" is clicked, execute the detector on the test input and display results.

### 5b.6 Notes on Testing

#### For PyRIT:
- Ensure that the orchestrator used for testing is properly initialized with the necessary target and configurations.
- Testing should simulate the actual usage as closely as possible.

#### For Garak:
- Some detectors may depend on additional context or specific fields in the `Attempt` object. Ensure these are provided if necessary.
- Remember that detectors typically return an iterable of floats, representing detection scores.

## 5d. Next Steps

### Display:
- A "Next Step" button to proceed to "Configure Orchestrators".

### Action:
- User clicks "Next Step".

### Backend:
- Ensure that all configured scorers or detectors are properly saved and any required configurations are completed.

## Additional Notes:

### Integration with Orchestrators:
- For **PyRIT**, ensure that when testing scorers, an orchestrator like `PromptSendingOrchestrator` is used to simulate the actual flow.
- For **Garak**, note that detectors are usually used within a harness during a probe run. Testing should take this into consideration.

### Consistent Terminology:
- Clearly differentiate between Scorers (PyRIT) and Detectors (Garak) in the UI and instructions.

### Error Handling:
- Use try-except blocks to handle exceptions during testing and provide user-friendly error messages.

### Parameter Files:
- Update parameter files with the configurations of scorers or detectors for later use in the pipeline.

### User Guidance:
- Provide help texts and tooltips to assist users in configuring and testing scorers or detectors.

### Data Validation:
- Ensure that all user inputs are validated before use.