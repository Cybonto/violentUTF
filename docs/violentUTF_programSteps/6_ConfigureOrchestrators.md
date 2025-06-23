# 6. Configure Orchestrators

In this section, you will configure an **Orchestrator** to define how the system interacts with the Generator and other components. Orchestrators implement attack strategies or workflows by coordinating Generators, Datasets, Converters, Scorers (PyRIT), Probes, and Detectors (Garak).

**Note:** In **PyRIT**, Orchestrators are components that implement attack strategies.
**Note:** In **Garak**, the equivalent component is called a **Harness**, which runs Probes through Generators and applies Detectors to evaluate the outputs.

We will use **"Orchestrator"** as a general term to refer to both PyRIT Orchestrators and Garak Harnesses.

## 6a. Initial Display

### Display:
- **Heading:** "Configure Orchestrator".
- **Help Text:** "Select an Orchestrator to define how the system interacts with the Generator and other components. Different Orchestrators implement different attack strategies or workflows."

### Backend:
- Determine if the pipeline is PyRIT-based or Garak-based:
  - If PyRIT-based pipeline, display options for Orchestrators.
  - If Garak-based pipeline, display options for Harnesses.

### Action:
- Display options based on the pipeline type.

## 6b. Configure Orchestrator Parameters (Conditional Form)

### For PyRIT-based pipeline:

### Display:
- A dynamic form based on the selected Orchestrator, including required and optional parameters.

### Action:
- The user fills in these fields.

### Backend:
- Store all parameters in `st.session_state["current_orchestrator_params"]`.
- Update the parameter file with user-specified orchestrator settings.

### For Garak-based pipeline:

### Display:
- A dynamic form based on the selected Harness, including required and optional parameters.

### Action:
- User fills in the required and optional fields.

### Backend:
- Store parameters in `st.session_state["current_harness_params"]`.
- Update the parameter file with the harness settings.

## 6c. Create and Store Orchestrator

### Display:
- A **"Create Orchestrator"** button.

### Action:
- When clicked, the system validates the inputs and saves the configuration.

### Backend:
- Validate the inputs and save the orchestrator configuration in the parameter file.

## 6d. Display Configured Orchestrators

### Display:
- A list or table of configured Orchestrators and/or Harnesses, showing for each:
  - Name.
  - Description.
  - "Edit", "Test", and "Remove" buttons.

### Action:
- User can manage orchestrators using the provided options.

### Backend:
- Implement functionality for Edit, Test, and Remove actions.
- Update `st.session_state` and the parameter file accordingly.

## 6e. Testing the Orchestrator

### For PyRIT-based pipeline:

### Display:
- A section titled **"Test Orchestrator"**.
- A **"Run Test"** button.

### Action:
- User provides test inputs and clicks **"Run Test"**.

### Backend:
- Retrieve the orchestrator instance.
- Capture and display outputs or errors.

### Display:
- Show the results of the test, including any outputs and logs.

### For Garak-based pipeline:

### Display:
- **"Test Harness"** section.

### Action:
- User clicks **"Run Test"**.

### Backend:
- Retrieve the harness configuration.
- Display the test execution results.

## 6f. Running the Orchestrator

Once the orchestrators are configured and tested, you can execute them to perform the attacks or evaluations.

### Display:
- **Heading:** "Run Orchestrator".
- A progress bar and log display area to show execution status.

### Action:
- User selects an orchestrator and clicks **"Run Orchestrator"**.

### Backend:
- Retrieve the selected Pyrit's orchestrator instance or Garak's harness configuration.
- Handle asynchronous execution appropriately.

### Display:
- Upon completion, display a summary of results and any relevant outputs.
- Provide an option to download logs or reports.

## 6g. Error Handling and Considerations

### Validation:
- Ensure all required inputs are provided before creation or execution.
- Validate that components are compatible (e.g., correct types).

### Error Messages:
- Provide clear and actionable error messages.
- Use `st.error()` to display errors in the GUI.

### Exception Handling:
- Wrap execution calls in try-except blocks to catch and display exceptions.

### User Guidance:
- Include tooltips or help text for input fields to assist users.
- Inform users of any dependencies or prerequisites.

### Performance:
- For long-running orchestrators, update progress indicators to keep users informed.
- Avoid blocking the main thread; use asynchronous execution where appropriate.

### Persistence:
- Ensure that configurations are saved to the parameter file for future use.
- Provide options to export configurations.