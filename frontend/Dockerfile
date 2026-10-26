FROM node:22-alpine
WORKDIR /app
COPY package.json tsconfig.json next-env.d.ts ./
RUN npm install
COPY app ./app
ENV NEXT_TELEMETRY_DISABLED=1
CMD ["npm","run","dev","--","-H","0.0.0.0"]
