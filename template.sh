#!/bin/bash

# Backend
mkdir -p backend/app/{api,core,rag,vectorstore,multimodal,search}
touch backend/app/main.py
touch backend/requirements.txt

# Frontend
npx create-next-app@latest frontend --ts --app --no-eslint --no-tailwind --use-npm

echo "Project structure created successfully!"
