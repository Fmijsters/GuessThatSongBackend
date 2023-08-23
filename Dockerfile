FROM node:16-alpine3.17
WORKDIR /frontend
RUN npm install
CMD ["npm run start"]
EXPOSE 3000
