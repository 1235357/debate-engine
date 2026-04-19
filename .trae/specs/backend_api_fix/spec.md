# DebateEngine Backend API Fix - Product Requirement Document

## Overview
- **Summary**: Fix the LLM provider error in the backend API that's causing "LLM Provider NOT provided" errors when using NVIDIA models
- **Purpose**: To resolve the model format issue that's preventing the backend API from correctly calling NVIDIA models
- **Target Users**: Developers and users of DebateEngine who need the API to work correctly with NVIDIA models

## Goals
- Fix the NVIDIA model format issue in the LLM provider
- Ensure the API can correctly call NVIDIA models
- Verify that the fix resolves the error
- Test the fix with the frontend

## Non-Goals (Out of Scope)
- Changing other provider configurations
- Modifying frontend functionality
- Adding new features

## Background & Context
- The backend API is currently throwing errors when trying to use NVIDIA models: "LLM Provider NOT provided. Pass in the LLM provider you are trying to call. You passed model=minimaxai/minimax-m2.7"
- The issue is in the `_build_litellm_params` method of the `LLMProvider` class
- The current code is setting the model parameter to "minimaxai/minimax-m2.7" for NVIDIA, but LiteLLM expects a different format

## Functional Requirements
- **FR-1**: Fix the NVIDIA model format in the LLM provider
- **FR-2**: Ensure the API can correctly call NVIDIA models
- **FR-3**: Test the fix with the frontend

## Non-Functional Requirements
- **NFR-1**: The fix should be minimal and focused on the specific issue
- **NFR-2**: The fix should not break other provider functionality
- **NFR-3**: The fix should be backward compatible

## Constraints
- **Technical**: Must work with LiteLLM's NVIDIA provider format
- **Business**: Must maintain compatibility with existing code

## Assumptions
- The backend API is otherwise functional
- The frontend is correctly configured to call the API
- NVIDIA API keys are properly set up

## Acceptance Criteria

### AC-1: NVIDIA Model Format Fix
- **Given**: The backend API is running
- **When**: A request is made to use an NVIDIA model
- **Then**: The API should correctly format the model parameter for LiteLLM
- **Verification**: `programmatic`

### AC-2: API Functionality
- **Given**: The fix is implemented
- **When**: The frontend calls the API with an NVIDIA model
- **Then**: The API should successfully process the request
- **Verification**: `programmatic`

### AC-3: Error Resolution
- **Given**: The fix is implemented
- **When**: The frontend calls the API
- **Then**: The "LLM Provider NOT provided" error should not appear
- **Verification**: `programmatic`

## Open Questions
- [ ] What is the correct model format for NVIDIA models in LiteLLM?
- [ ] Are there any other provider-specific formatting issues?
