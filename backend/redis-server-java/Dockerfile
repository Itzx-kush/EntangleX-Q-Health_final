FROM eclipse-temurin:25-jdk AS build
WORKDIR /src
COPY backend/redis-server-java/src/main/java/ ./
RUN mkdir -p /out && javac --enable-preview --release 25 -d /out ./*.java

FROM eclipse-temurin:25-jre
WORKDIR /app
COPY --from=build /out /app/classes
RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 6380
CMD ["java", "--enable-preview", "-cp", "/app/classes", "Main", "--port", "6380", "--dir", "/data", "--appendonly", "yes"]
