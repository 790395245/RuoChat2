# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RuoChat2 is an intelligent message processing and auto-reply system. The system combines AI-driven decision making with scheduled tasks to handle message interactions automatically.

## System Architecture

The system is built around four core modules:

### 1. Trigger Mechanisms
- **User Message Trigger**: Real-time responses to incoming user messages
- **Autonomous Trigger**: System-initiated scheduled tasks (daily at 00:00 and 00:05)
- **Reply Task Trigger**: Execution trigger for queued reply tasks

### 2. Data Storage Layer (Five Databases)
- **Prompt Library** (灰色/提示词库): Stores character settings and system prompts
- **Memory Library** (黄色/记忆库): Stores hot topics and user memory points with strength/weight attributes
- **Planned Task Library** (红色/计划任务库): Stores daily scheduled tasks
- **Reply Task Library** (蓝色/回复任务库): Stores pending reply tasks (both user-triggered and autonomous)
- **Message Record Library** (绿色/消息记录库): Stores all interaction messages (received/sent)

### 3. AI Decision Nodes
The system uses multiple AI decision points:
- **Hot Topic Judgment**: Determines if news/events are worth remembering
- **Reply Content & Timing**: Decides when and how to reply to messages
- **Memory Point Detection**: Identifies memorable moments with strength/forgetting-time/weight
- **Daily Task Planning**: Generates full-day planned tasks
- **Autonomous Message Triggering**: Creates proactive outgoing messages

### 4. Context Enhancement
Before each AI decision, the system retrieves context from relevant databases through Vertical Container aggregators that bundle multiple data sources for efficient context retrieval.

## Core Workflow Stages

### Stage 1: System Configuration Initialization
1. Character settings → Written to Prompt Library
2. Hot topics → AI evaluates → Written to Memory Library
3. Trigger modes initialized

### Stage 2: User Message Processing
1. Incoming message → Written to Message Record Library
2. Context retrieved from all databases via Vertical Container
3. AI decides reply content and timing → Written to Reply Task Library
4. AI checks for memory points → Written/strengthened in Memory Library
5. Syncs with other auto-reply tasks for consistency

### Stage 3: Autonomous Scheduled Tasks
- **00:00 Task**: AI generates daily planned tasks → Written to Planned Task Library
- **00:05 Task**: AI generates autonomous trigger messages → Written to Reply Task Library

### Stage 4: Reply Execution
Reply Task Trigger → Executes tasks from Reply Task Library → Sends messages → Records to Message Record Library

## Key Design Principles

1. **Dual-Mode Operation**: Supports both reactive (user-triggered) and proactive (scheduled) interactions
2. **AI-Driven Logic**: AI handles not just content generation but also memory management, task categorization, and timing decisions
3. **Complete Data Persistence**: All critical data flows through databases for traceability and context recall
4. **Modular Design**: Container nodes aggregate multi-database resources; AI decision nodes depend on Prompt Library for consistency
