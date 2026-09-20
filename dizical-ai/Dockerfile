FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY src/ ./src/
COPY scripts/ ./scripts/
EXPOSE 8080
CMD ["node", "src/index.js"]