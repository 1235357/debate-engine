# Debate Engine - Version and Demo Improvements

## Overview
- **Summary**: Improve the Debate Engine project by adding version number display, preset inputs, and AI reasoning visualization to the GitHub Pages demo, while ensuring all changes are synced to the main branch.
- **Purpose**: Enhance user experience, showcase core functionality, and maintain version control for the project.
- **Target Users**: Developers, testers, and potential users of the Debate Engine.

## Goals
- Add version number to project, visible on GitHub Pages demo (hidden until hover)
- Sync all changes to main branch through PR
- Add preset inputs to demo page
- Visualize internal AI reasoning process in demo
- Fix existing LLM provider issues

## Non-Goals (Out of Scope)
- Complete rewrite of the codebase
- Adding new features beyond the specified requirements
- Changing the core architecture of the system

## Background & Context
- The project is a multi-agent system that uses LLM providers for debate and analysis
- It has a GitHub Pages demo and is deployed on Render
- Current issues include LLM provider configuration errors and lack of version visibility
- Previous fixes have addressed API server issues and accessibility improvements

## Functional Requirements
- **FR-1**: Display version number on GitHub Pages demo, hidden until hover
- **FR-2**: Add preset input examples to demo page
- **FR-3**: Visualize internal AI reasoning process in demo
- **FR-4**: Fix LLM provider configuration issues
- **FR-5**: Sync all changes to main branch through PR

## Non-Functional Requirements
- **NFR-1**: Version number should be automatically generated from git commit information
- **NFR-2**: AI reasoning visualization should be clear and detailed
- **NFR-3**: All changes should pass GitHub Actions CI/CD checks
- **NFR-4**: Demo should maintain accessibility standards

## Constraints
- **Technical**: Must work with existing codebase and deployment setup
- **Business**: Must not introduce breaking changes
- **Dependencies**: Relies on LiteLLM for LLM provider integration

## Assumptions
- The project has a working generate_version.py script
- The demo page is located at demo/index.html
- The API server is deployed on Render

## Acceptance Criteria

### AC-1: Version Number Display
- **Given**: GitHub Pages demo is loaded
- **When**: User hovers over version badge location
- **Then**: Version number (based on git commit) is displayed
- **Verification**: `human-judgment`

### AC-2: Preset Inputs
- **Given**: Demo page is loaded
- **When**: User clicks on preset input buttons
- **Then**: Corresponding input is populated in the text area
- **Verification**: `human-judgment`

### AC-3: AI Reasoning Visualization
- **Given**: User submits a query through the demo
- **When**: API processes the request
- **Then**: Detailed AI reasoning steps are displayed in real-time
- **Verification**: `human-judgment`

### AC-4: LLM Provider Fix
- **Given**: API receives a request
- **When**: LLM provider is called
- **Then**: No "LLM Provider NOT provided" error occurs
- **Verification**: `programmatic`

### AC-5: Sync to Main Branch
- **Given**: Changes are made to codebase
- **When**: PR is created and merged
- **Then**: All changes are present in main branch
- **Verification**: `programmatic`

## Open Questions
- [ ] What specific preset inputs should be included?
- [ ] How detailed should the AI reasoning visualization be?
- [ ] Are there any additional CI/CD checks that need to pass?