// ═══════════════════════════════════════════════════════════════════════════
// MERGED PIPELINE
//   Stage group A (unchanged, "his"):  Build Optimizer  — selective build/test
//     + carbon-aware BUILD scheduling (beliver247/green-release-app)
//   Stage group B (unchanged, "mine"): Deployment Optimizer — AI-picked
//     deploy strategy (canary/rolling/recreate) + carbon tracking (Components
//     1 & 2 of the dissertation, via the green-agent shared library)
//
// NOTE (demo-mode edit): all remote-deploy stages that used to SSH into
// the OPC box (147.15.144.192) now run the same docker/docker-compose
// commands directly on the Jenkins agent instead. This avoids the
// intermittent "connection refused" from that host. REMOTE_HOST /
// REMOTE_PORT / REMOTE_USER / SSH_CREDENTIALS are left declared below
// but unused — flip the deploy stages back to sshagent+ssh if you need
// real remote deploys again later.
//
// ASSUMPTIONS MADE WHILE MERGING (check these before running):
//   1. DOCKER_HUB_CREDENTIALS: his pipeline never pushed to Docker Hub (it
//      deployed locally), so there was no credential of "his" to reuse for
//      pushing beliver247/green-release-app. Using your
//      'dockerhub-hiran-credentials' id here — swap if there's a shared one.
//   2. Health-check port for local deploys is 8080 (from your original
//      docker-compose-based deploy).
//   3. docker-compose.yml is expected at the repo root inside env.WORK_DIR
//      (same assumption his "Deploy Locally" stage made).
//   4. CANARY_CONTAINER renamed to green-release-canary to match the new app.
// ═══════════════════════════════════════════════════════════════════════════

@Library('green-agent') _

// ─────────────────────────────────────────────────────────────────────────
// Groovy helpers (from the build-optimization pipeline — unchanged)
// ─────────────────────────────────────────────────────────────────────────
def greenReleaseModules() {
    return ['core', 'service', 'api', 'app']
}

def buildMockCarbonData() {
    def now = new Date()
    def entries = (0..24).collect { h ->
        def ts = new Date(now.time - (24 - h) * 3600000L)
        def isoTs = ts.format("yyyy-MM-dd'T'HH:mm:ss")
        def intensity = String.format("%.1f", 310.0 + h * 0.4)
        "{\"timestamp\":\"${isoTs}\",\"intensity\":${intensity}}"
    }
    return [
            history:  '[' + entries.join(',') + ']',
            forecast: '[{"hour":1,"intensity":300.0},{"hour":2,"intensity":250.0},{"hour":3,"intensity":180.0}]'
    ]
}

def serializeCarbonHistory(histList) {
    def entries = histList.collect { h ->
        "{\"timestamp\":\"${h.timestamp}\",\"intensity\":${h.intensity}}"
    }
    return '[' + entries.join(',') + ']'
}

def serializeCarbonForecast(forecastList) {
    def entries = forecastList.collect { f ->
        "{\"hour\":${f.hour},\"intensity\":${f.intensity}}"
    }
    return '[' + entries.join(',') + ']'
}

def discoverModuleTestInventory() {
    def inventory = [:]
    greenReleaseModules().each { moduleName ->
        def countText = sh(
                script: '''
                module="''' + moduleName + '''"
                if [ -d "$module/src/test/java" ]; then
                  grep -Rho '@Test' "$module/src/test/java" --include='*.java' 2>/dev/null | wc -l | tr -d ' '
                else
                  echo 0
                fi
            ''',
                returnStdout: true
        ).trim()
        inventory[moduleName] = countText ? countText.toInteger() : 0
    }
    return inventory
}

def readSurefireTestCounts() {
    def counts = [:]
    greenReleaseModules().each { moduleName ->
        def countText = sh(
                script: '''
                module="''' + moduleName + '''"
                report_dir="$module/target/surefire-reports"
                if [ -d "$report_dir" ] && find "$report_dir" -name 'TEST-*.xml' -type f | grep -q .; then
                  find "$report_dir" -name 'TEST-*.xml' -type f -exec awk 'BEGIN { total = 0 } /<testsuite / { if (match($0, /tests="[0-9]+"/)) { value = substr($0, RSTART + 7, RLENGTH - 8); total += value } } END { print total }' {} +
                else
                  echo 0
                fi
            ''',
                returnStdout: true
        ).trim()
        counts[moduleName] = countText ? countText.toInteger() : 0
    }
    return counts
}

def affectedModuleSet() {
    if (env.AFFECTED_MODULES == 'all') {
        return greenReleaseModules() as Set
    }
    if (!env.AFFECTED_MODULES?.trim()) {
        return [] as Set
    }
    return env.AFFECTED_MODULES.split(',').collect { it.trim() }.findAll { it } as Set
}

// Whether the app image actually needs to be (re)built/deployed this run —
// used to gate Docker Build / Push / the whole deployment-optimizer group.
def appAffected() {
    return env.AFFECTED_MODULES == 'all' || env.AFFECTED_MODULES?.split(',')?.contains('app')
}

pipeline {
    agent any

    parameters {
        booleanParam(
                name: 'DRY_RUN',
                defaultValue: false,
                description: 'When true, only run the optimizer analysis without building, testing, or deploying.'
        )
        booleanParam(
                name: 'FORCE_FULL_BUILD',
                defaultValue: false,
                description: 'Skip the optimizer analysis and force a full build and test of all modules.'
        )
        booleanParam(
                name: 'ENABLE_GREEN_SCHEDULING',
                defaultValue: true,
                description: 'Allow the pipeline to delay the build until a greener time window.'
        )
        string(
                name: 'OVERRIDE_SCHEDULE_HOUR',
                defaultValue: 'auto',
                description: 'Override ML recommendation (e.g., "5" for 5 AM). Use "auto" to let the ML model decide.'
        )
    }

    environment {
        // ── Build-optimization app/creds ("his") ───────────────────────────
        DOCKER_IMAGE              = 'hiranx/green-release-app'
        DOCKER_TAG                = "${BUILD_NUMBER}"
        // NOTE (assumption #1 above): his pipeline had no Docker Hub push
        // step / credential of its own — reusing yours to push this image
        // so the remote host can pull it. Replace the id if there's a
        // shared credential you'd rather use.
        DOCKER_HUB_CREDENTIALS    = credentials('dockerhub-hiran-credentials')
        DASHBOARD_URL             = 'http://host.docker.internal:5003'
        ELECTRICITY_MAPS_API_KEY  = 'em_nGgVAPUefFX2qe8BkqzFgw3n8uGpJE2J'

        // ── Deployment-optimization settings ("mine") ──────────────────────
        // Left in place but unused now that deploys run locally — see note
        // at the top of the file if you want to switch back to remote.
        REMOTE_HOST         = '147.15.144.192'
        REMOTE_PORT         = '2510'
        REMOTE_USER         = 'hiran'
        SSH_CREDENTIALS     = 'ubuntu-pc-ssh-hiran'

        METRICS_URL         = 'http://172.17.0.1:5001'   // Component 1: carbon/deployment tracker
        GREEN_AGENT_URL     = 'http://172.17.0.1:5002'   // Component 2: AI Green Deployment Decision Engine

        CANARY_WEIGHT       = '20'
        CANARY_WAIT_SECS    = '60'
        CANARY_CONTAINER    = 'green-release-canary'
        ROLLING_WAIT_SECS   = '15'

        // Set at runtime by the AI agent in "Green AI Check"
        DEPLOY_STRATEGY     = 'rolling'
    }

    stages {

        // ═════════════════════════════════════════════════════════════════
        //  GROUP A — BUILD OPTIMIZER (unchanged, "his")
        // ═════════════════════════════════════════════════════════════════

        stage('Init Build Metadata') {
            steps {
                script {
                    env.PIPELINE_START = System.currentTimeMillis().toString()
                    env.COMMIT_SHA = ''
                    env.COMMIT_MSG = ''
                    env.WORK_DIR = fileExists('pom.xml') ? '.' : 'green-release-demo'
                }
            }
        }

        stage('Setup Tools') {
            steps {
                script {
                    def workspace = pwd()
                    echo "Setting up local tool binaries (Docker CLI, Maven, and Docker Compose)..."

                    sh 'mkdir -p tool-bin'

                    if (sh(script: 'command -v docker >/dev/null 2>&1', returnStatus: true) != 0) {
                        if (!fileExists('tool-bin/docker')) {
                            echo "Docker CLI not found. Downloading static binary..."
                            sh '''
                                curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz -o docker.tgz
                                tar -xzf docker.tgz --strip-components=1 -C tool-bin docker/docker
                                rm -f docker.tgz
                                chmod +x tool-bin/docker
                            '''
                        }
                    } else {
                        echo "System docker command is already available."
                    }

                    if (sh(script: 'command -v docker-compose >/dev/null 2>&1', returnStatus: true) != 0) {
                        if (!fileExists('tool-bin/docker-compose')) {
                            echo "Docker Compose not found. Downloading static binary..."
                            sh '''
                                curl -fsSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 -o tool-bin/docker-compose
                                chmod +x tool-bin/docker-compose
                            '''
                        }
                    } else {
                        echo "System docker-compose command is already available."
                    }

                    if (sh(script: 'command -v mvn >/dev/null 2>&1', returnStatus: true) != 0) {
                        if (!fileExists('tool-bin/maven/bin/mvn')) {
                            echo "Maven not found. Downloading Apache Maven..."
                            sh '''
                                curl -fsSL https://archive.apache.org/dist/maven/maven-3/3.9.6/binaries/apache-maven-3.9.6-bin.tar.gz -o maven.tar.gz
                                mkdir -p tool-bin/maven
                                tar -xzf maven.tar.gz -C tool-bin/maven --strip-components=1
                                rm -f maven.tar.gz
                                chmod +x tool-bin/maven/bin/mvn
                            '''
                        }
                    } else {
                        echo "System mvn command is already available."
                    }

                    env.PATH = "${workspace}/tool-bin:${workspace}/tool-bin/maven/bin:${env.PATH}"
                    sh 'docker --version'
                    sh 'mvn --version'
                }
            }
        }

        stage('Checkout') {
            steps {
                script {
                    sh "git config --global --add safe.directory '*'"
                    if (!fileExists('pom.xml')) {
                        echo "Checking out green-release-demo..."
                        dir(env.WORK_DIR) {
                            checkout([$class: 'GitSCM',
                                      branches: [[name: '*/main']],
                                      userRemoteConfigs: [[
                                                                  url: 'https://github.com/Beliver-247/green-release-demo.git'
                                                          ]],
                                      extensions: [[ $class: 'CloneOption', shallow: false, depth: 0, noTags: false ]]
                            ])
                        }
                    } else {
                        echo "Found pom.xml in workspace root. Using existing root checkout."
                        sh "git status || echo 'Not a git repo'"
                        sh "git rev-parse HEAD || echo 'No git commit'"
                        echo "Forcing checkout of latest main..."
                        sh """
                            git fetch origin main || true
                            git checkout -B main origin/main || true
                            git pull origin main || true
                        """
                    }
                    dir(env.WORK_DIR) {
                        env.COMMIT_SHA = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                        env.COMMIT_MSG = sh(script: 'git log -1 --pretty=%s', returnStdout: true).trim()

                        // Urgent deploy bypass — skip all green checks
                        if (env.COMMIT_MSG.toLowerCase().contains('[urgent]')) {
                            env.URGENT_DEPLOY = 'true'
                            echo "⚡ URGENT deployment detected in commit message — all green checks will be skipped"
                        } else {
                            env.URGENT_DEPLOY = 'false'
                        }

                        if (fileExists('.last_built_commit')) {
                            env.GIT_PREVIOUS_SUCCESSFUL_COMMIT = readFile('.last_built_commit').trim()
                        } else {
                            env.GIT_PREVIOUS_SUCCESSFUL_COMMIT = 'null'
                        }
                    }
                }
            }
        }

        stage('Build Optimizer - Analyze') {
            steps {
                dir(env.WORK_DIR) {
                    script {
                        if (params.FORCE_FULL_BUILD) {
                            echo "=== FORCE_FULL_BUILD is enabled. Skipping Optimizer analysis ==="
                            env.OPTIMIZER_STATUS = 'success'
                            env.AFFECTED_MODULES = 'all'
                            env.MAVEN_BUILD_COMMANDS = 'mvn clean install -DskipTests'
                            env.MAVEN_TEST_COMMANDS = 'mvn test'
                            env.OPTIMIZER_DURATION = '0'
                            def mockCarbon = buildMockCarbonData()
                            env.CARBON_INTENSITY    = '320.0'
                            env.GREEN_PROBABILITY   = '0.35'
                            env.SCHEDULING_ACTION   = 'execute_now'
                            env.SCHEDULING_ENGINE   = 'mock'
                            env.SCHEDULED_HOUR      = ''
                            env.TARGET_INTENSITY    = ''
                            env.CARBON_HISTORY      = mockCarbon.history
                            env.CARBON_FORECAST     = mockCarbon.forecast
                            return
                        }

                        def analyzeStart = System.currentTimeMillis()
                        def output = sh(
                                script: '''
                                EXIT_CODE=0
                                tar -C "$PWD" -cf - . | docker run --rm -i \
                                  -e ELECTRICITY_MAPS_API_KEY="''' + (env.ELECTRICITY_MAPS_API_KEY ?: '') + '''" \
                                  -e GIT_PREVIOUS_SUCCESSFUL_COMMIT="''' + env.GIT_PREVIOUS_SUCCESSFUL_COMMIT + '''" \
                                  -e GIT_PREVIOUS_COMMIT="''' + env.GIT_PREVIOUS_COMMIT + '''" \
                                  -e GIT_COMMIT="''' + env.GIT_COMMIT + '''" \
                                  -v /var/run/docker.sock:/var/run/docker.sock \
                                  beliver247/build-optimizer-agent:latest \
                                  bash -lc '
                                    set -e
                                    mkdir -p /work
                                    tar -xf - -C /work
                                    cd /work
                                    git config --global --add safe.directory /work

                                    python3 -m optimizer \
                                      --project-root /work \
                                      --dry-run true \
                                      --output-format json \
                                      --carbon-aware
                                  ' || EXIT_CODE=$?

                                if [ "$EXIT_CODE" -eq 1 ]; then
                                  echo "OPTIMIZER_ERROR"
                                  exit 1
                                fi
                            ''',
                                returnStdout: true
                        ).trim()

                        env.OPTIMIZER_DURATION = ((System.currentTimeMillis() - analyzeStart) / 1000.0).toString()

                        echo "=== Build Optimizer Output ==="
                        echo output
                        echo "=============================="

                        def jsonLine = output.readLines().find { it.startsWith('{"') }
                        if (jsonLine) {
                            def result = new groovy.json.JsonSlurper().parseText(jsonLine)
                            env.OPTIMIZER_STATUS = result.status ?: 'unknown'

                            def buildCommands = []
                            def testCommands = []
                            for (action in result.actions) {
                                if (action.name == 'build') {
                                    buildCommands.add(action.command.join(' '))
                                } else if (action.name == 'test') {
                                    testCommands.add(action.command.join(' '))
                                }
                            }
                            env.MAVEN_BUILD_COMMANDS = buildCommands.join('|||')
                            env.MAVEN_TEST_COMMANDS = testCommands.join('|||')

                            def affectedModules = result.affected_modules ?: []
                            env.AFFECTED_MODULES = affectedModules.join(',')

                            echo "Optimizer status: ${env.OPTIMIZER_STATUS}"
                            echo "Affected modules: ${env.AFFECTED_MODULES}"
                            echo "Build commands: ${env.MAVEN_BUILD_COMMANDS}"
                            echo "Test commands: ${env.MAVEN_TEST_COMMANDS}"

                            if (result.scheduling) {
                                env.CARBON_INTENSITY = result.scheduling.current_intensity?.toString() ?: ''
                                env.GREEN_PROBABILITY = result.scheduling.green_probability?.toString() ?: ''
                                env.SCHEDULING_ACTION = result.scheduling.action ?: ''
                                env.SCHEDULING_ENGINE = result.scheduling.engine ?: ''
                                env.SCHEDULED_HOUR = result.scheduling.scheduled_hour?.toString() ?: ''
                                env.TARGET_INTENSITY = result.scheduling.target_intensity?.toString() ?: ''
                                if (result.scheduling.carbon_history) {
                                    env.CARBON_HISTORY = serializeCarbonHistory(result.scheduling.carbon_history)
                                } else {
                                    echo "[GreenOptimizer] carbon_history missing from optimizer output. Using mock history."
                                    env.CARBON_HISTORY = buildMockCarbonData().history
                                }
                                if (result.scheduling.carbon_forecast) {
                                    env.CARBON_FORECAST = serializeCarbonForecast(result.scheduling.carbon_forecast)
                                } else {
                                    env.CARBON_FORECAST = buildMockCarbonData().forecast
                                }
                            } else {
                                echo "[GreenOptimizer] No scheduling data in optimizer output. Using mock carbon data."
                                def mockCarbon = buildMockCarbonData()
                                env.CARBON_INTENSITY    = '320.0'
                                env.GREEN_PROBABILITY   = '0.35'
                                env.SCHEDULING_ACTION   = 'execute_now'
                                env.SCHEDULING_ENGINE   = 'mock'
                                env.SCHEDULED_HOUR      = ''
                                env.TARGET_INTENSITY    = ''
                                env.CARBON_HISTORY      = mockCarbon.history
                                env.CARBON_FORECAST     = mockCarbon.forecast
                            }
                        } else {
                            env.OPTIMIZER_STATUS = 'no_changes'
                            env.MAVEN_BUILD_COMMANDS = ''
                            env.MAVEN_TEST_COMMANDS = ''
                            env.AFFECTED_MODULES = ''
                        }

                        if (params.DRY_RUN) {
                            echo "=== DRY RUN MODE — Skipping build, test, Docker, and deploy stages ==="
                        }
                    }
                }
            }
        }

        stage('Green Scheduling') {
            when {
                expression {
                    params.ENABLE_GREEN_SCHEDULING &&
                            env.OPTIMIZER_STATUS == 'success' &&
                            env.URGENT_DEPLOY != 'true'   // skip if urgent
                }
            }
            steps {
                script {
                    def targetHourStr = params.OVERRIDE_SCHEDULE_HOUR
                    def shouldSchedule = false
                    def targetHour = 0

                    if (targetHourStr != 'auto') {
                        targetHour = targetHourStr.toInteger()
                        echo "Developer OVERRIDE: Scheduling build for ${targetHour}:00."
                        shouldSchedule = true
                    } else if (env.SCHEDULING_ACTION == 'schedule' && env.SCHEDULED_HOUR) {
                        targetHour = env.SCHEDULED_HOUR.toInteger()
                        echo "Carbon intensity is high (${env.CARBON_INTENSITY}). ML Model recommends delaying until ${targetHour}:00."
                        shouldSchedule = true
                    } else if (env.SCHEDULING_ACTION == 'execute_now') {
                        echo "ML Model says it's a Green Window right now! Proceeding with build."
                    }

                    if (shouldSchedule) {
                        def now = new Date()
                        def currentHour = now.getHours()
                        def hoursToWait = targetHour - currentHour
                        if (hoursToWait <= 0) {
                            hoursToWait += 24
                        }

                        def delayInSeconds = hoursToWait * 3600

                        echo "Queueing a new build to start in ${hoursToWait} hours (${delayInSeconds} seconds)..."

                        build job: env.JOB_NAME, quietPeriod: delayInSeconds, wait: false, parameters: [
                                booleanParam(name: 'ENABLE_GREEN_SCHEDULING', value: false),
                                booleanParam(name: 'DRY_RUN', value: params.DRY_RUN),
                                booleanParam(name: 'FORCE_FULL_BUILD', value: params.FORCE_FULL_BUILD),
                                string(name: 'OVERRIDE_SCHEDULE_HOUR', value: 'auto')
                        ]

                        currentBuild.description = "Rescheduled for ${targetHour}:00"
                        env.IS_RESCHEDULED = 'true'
                        currentBuild.result = 'ABORTED'
                        error("Pipeline rescheduled to a greener window at ${targetHour}:00 to save carbon.")
                    }
                }
            }
        }

        stage('Selective Build') {
            when {
                expression { !params.DRY_RUN && env.OPTIMIZER_STATUS == 'success' && env.MAVEN_BUILD_COMMANDS?.trim() }
            }
            steps {
                dir(env.WORK_DIR) {
                    script {
                        def buildStart = System.currentTimeMillis()
                        echo "Running selective Maven build for modules: ${env.AFFECTED_MODULES}"
                        env.MAVEN_BUILD_COMMANDS.split('\\|\\|\\|').each { cmd ->
                            echo "Executing: ${cmd}"
                            sh cmd
                        }
                        env.BUILD_DURATION = ((System.currentTimeMillis() - buildStart) / 1000.0).toString()
                    }
                }
            }
        }

        stage('Selective Test') {
            when {
                expression { !params.DRY_RUN && env.OPTIMIZER_STATUS == 'success' && env.MAVEN_TEST_COMMANDS?.trim() }
            }
            steps {
                dir(env.WORK_DIR) {
                    script {
                        def testStart = System.currentTimeMillis()
                        echo "Running selective tests for modules: ${env.AFFECTED_MODULES}"

                        def testOutput = ''
                        env.MAVEN_TEST_COMMANDS.split('\\|\\|\\|').each { cmd ->
                            echo "Executing: ${cmd}"
                            testOutput += sh(script: cmd, returnStdout: true)
                        }
                        env.TEST_DURATION = ((System.currentTimeMillis() - testStart) / 1000.0).toString()

                        def testsRun = 0
                        def testsSkipped = 0
                        def moduleDetails = [:]

                        def inventory = discoverModuleTestInventory()
                        def executed = readSurefireTestCounts()
                        def affected = affectedModuleSet()

                        greenReleaseModules().each { mod ->
                            def moduleTotal = inventory[mod] ?: 0
                            def moduleRun = affected.contains(mod) ? (executed[mod] ?: 0) : 0
                            def moduleSkipped = affected.contains(mod) ? 0 : moduleTotal
                            def status = affected.contains(mod) ? 'run' : 'skipped'

                            moduleDetails[mod] = ['status': status, 'run': moduleRun, 'skipped': moduleSkipped]
                            testsRun += moduleRun
                            testsSkipped += moduleSkipped
                        }

                        env.TESTS_EXECUTED = testsRun.toString()
                        env.TESTS_SKIPPED = testsSkipped.toString()
                        env.MODULE_DETAILS = groovy.json.JsonOutput.toJson(moduleDetails).replaceAll('"', '\\\\"')

                        echo "Total tests executed: ${env.TESTS_EXECUTED}"
                        echo "Total tests skipped: ${env.TESTS_SKIPPED}"
                        echo "Module Details: ${env.MODULE_DETAILS}"
                    }
                }
            }
        }

        stage('Docker Build') {
            when {
                expression { !params.DRY_RUN && appAffected() }
            }
            steps {
                dir(env.WORK_DIR) {
                    script {
                        def dockerStart = System.currentTimeMillis()
                        dir('app') {
                            echo "Building Docker image: ${DOCKER_IMAGE}:${DOCKER_TAG}"
                            // Also tag :canary so the deployment optimizer can use canary strategy.
                            sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} -t ${DOCKER_IMAGE}:latest -t ${DOCKER_IMAGE}:canary ."
                        }
                        env.DOCKER_BUILD_DURATION = ((System.currentTimeMillis() - dockerStart) / 1000.0).toString()
                    }
                }
            }
        }

        // NOTE: Docker Push isn't part of the SSH/OPC problem, so it's left
        // as-is. Since deploys are local now, this push isn't strictly
        // required for the demo to work, but keeping it doesn't hurt.
        stage('Docker Push') {
            when {
                expression { !params.DRY_RUN && appAffected() }
            }
            steps {
                sh """
                    echo "${DOCKER_HUB_CREDENTIALS_PSW}" | docker login -u "${DOCKER_HUB_CREDENTIALS_USR}" --password-stdin
                    docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                    docker push ${DOCKER_IMAGE}:latest
                    docker push ${DOCKER_IMAGE}:canary
                    docker logout
                    echo "[DOCKER] Push complete"
                """
            }
        }

        // ═════════════════════════════════════════════════════════════════
        //  GROUP B — DEPLOYMENT OPTIMIZER (unchanged, "mine")
        //  Only runs when the app image actually changed this build.
        //  Deploy stages below now run LOCALLY on the Jenkins agent —
        //  no more SSH to the OPC box.
        // ═════════════════════════════════════════════════════════════════

        stage('Green AI Check') {
            when {
                expression {
                    !params.DRY_RUN &&
                            appAffected() &&
                            env.URGENT_DEPLOY != 'true'
                }
            }

            steps {
                script {

                    // ============================================================
                    // CRITICAL FIX
                    //
                    // greenCheck() now RETURNS the strategy.
                    // We explicitly assign it to Jenkins env.
                    // ============================================================

                    def selectedStrategy = greenCheck()

                    if (!selectedStrategy) {
                        echo "⚠️ Green AI returned no strategy."
                        echo "   Using safe fallback: rolling"
                        selectedStrategy = 'rolling'
                    }

                    selectedStrategy =
                            selectedStrategy.toString().toLowerCase().trim()

                    // Validate before assigning
                    if (!(selectedStrategy in ['canary', 'rolling', 'recreate'])) {

                        echo "⚠️ Invalid deployment strategy returned: ${selectedStrategy}"
                        echo "   Using safe fallback: rolling"

                        selectedStrategy = 'rolling'
                    }

                    // Explicitly persist the strategy
                    env.DEPLOY_STRATEGY = selectedStrategy

                    echo "🌿 AI selected deployment strategy: ${env.DEPLOY_STRATEGY}"

                    // Final safety check
                    if (!(env.DEPLOY_STRATEGY in ['canary', 'rolling', 'recreate'])) {
                        error("Invalid deployment strategy: ${env.DEPLOY_STRATEGY}")
                    }
                }
            }
        }

        stage('Notify Deployment Start') {
            when {
                expression { !params.DRY_RUN && appAffected() }
            }
            steps { notifyStart() }
        }

        stage('Carbon Snapshot - Before') {
            when {
                expression { !params.DRY_RUN && appAffected() }
            }
            steps { carbonSnapshot(phase: 'before') }
        }

        // ── CANARY ──────────────────────────────────────────────────────
        stage('Deploy Canary') {
            when { expression { !params.DRY_RUN && appAffected() && env.DEPLOY_STRATEGY == 'canary' } }
            steps {
                sh """
                    set -e
                    echo "[CANARY] Pulling canary image..."
                    docker pull ${DOCKER_IMAGE}:canary

                    echo "[CANARY] Starting canary container on port 8880..."
                    docker rm -f ${CANARY_CONTAINER} 2>/dev/null || true
                    docker run -d \
                        --name ${CANARY_CONTAINER} \
                        -p 8880:8080 \
                        --label role=canary \
                        --label build=${BUILD_NUMBER} \
                        ${DOCKER_IMAGE}:canary

                    sleep 10
                    curl -sf http://localhost:8880/health && echo "[CANARY] Canary healthy" || exit 1
                """
                carbonSnapshot(phase: 'canary_live', infraMultiplier: '1.2', canaryWeight: env.CANARY_WEIGHT, note: 'stable_plus_canary_running')
            }
        }

        stage('Observe Canary') {
            when { expression { !params.DRY_RUN && appAffected() && env.DEPLOY_STRATEGY == 'canary' } }
            steps {
                echo "Observing canary for ${CANARY_WAIT_SECS}s..."
                sleep time: "${CANARY_WAIT_SECS}", unit: 'SECONDS'
                sh """
                    set -e
                    echo "[CANARY] Health check..."
                    curl -sf http://localhost:8880/health

                    echo "[CANARY] Error rate check (last 60s)..."
                    ERROR_COUNT=\$(docker logs --since=60s ${CANARY_CONTAINER} 2>&1 | grep -ci ERROR || true)
                    echo "Errors detected: \$ERROR_COUNT"

                    if [ "\$ERROR_COUNT" -gt 5 ]; then
                        echo "[CANARY] Too many errors - triggering rollback"
                        exit 1
                    fi
                    echo "[CANARY] Error rate acceptable"
                """
            }
        }

        stage('Promote Canary') {
            when { expression { !params.DRY_RUN && appAffected() && env.DEPLOY_STRATEGY == 'canary' } }
            steps {
                dir(env.WORK_DIR) {
                    sh """
                        set -e
                        echo "[CANARY] Promoting: tag canary as latest..."
                        docker tag ${DOCKER_IMAGE}:canary ${DOCKER_IMAGE}:latest

                        echo "[CANARY] Restarting stable with promoted image..."
                        docker-compose down
                        docker-compose up -d

                        echo "[CANARY] Removing canary sidecar..."
                        docker rm -f ${CANARY_CONTAINER} || true

                        sleep 15
                        docker-compose ps
                    """
                }
                carbonSnapshot(phase: 'promoted', infraMultiplier: '1.0', note: 'canary_removed_stable_updated')
            }
        }

        // ── ROLLING ─────────────────────────────────────────────────────
        stage('Deploy Rolling') {
            when { expression { !params.DRY_RUN && appAffected() && env.DEPLOY_STRATEGY == 'rolling' } }
            steps {
                dir(env.WORK_DIR) {
                    sh """
                        set -e
                        echo "[ROLLING] Pulling new image..."
                        docker pull ${DOCKER_IMAGE}:latest

                        CONTAINERS=\$(docker-compose ps -q)
                        TOTAL=\$(echo "\$CONTAINERS" | wc -w)
                        echo "[ROLLING] Found \$TOTAL containers to roll"

                        for CONTAINER in \$CONTAINERS; do
                            NAME=\$(docker inspect --format="{{.Name}}" \$CONTAINER | sed "s#^/##")
                            echo "[ROLLING] Replacing \$NAME..."
                            docker stop --time=10 \$CONTAINER || true
                            docker-compose up -d --no-deps 2>/dev/null || true
                            sleep ${ROLLING_WAIT_SECS}
                            curl -sf http://localhost:8080/health || (echo "Health check failed"; exit 1)
                            echo "[ROLLING] \$NAME replaced successfully"
                        done

                        docker-compose ps
                    """
                }
                carbonSnapshot(phase: 'during', infraMultiplier: '1.1')
            }
        }

        // ── RECREATE ────────────────────────────────────────────────────
        stage('Deploy Recreate') {
            when { expression { !params.DRY_RUN && appAffected() && env.DEPLOY_STRATEGY == 'recreate' } }
            steps {
                dir(env.WORK_DIR) {
                    sh """
                        set -e
                        echo "[RECREATE] Stopping all containers..."
                        docker-compose down

                        echo "[RECREATE] Pulling new image..."
                        docker pull ${DOCKER_IMAGE}:latest

                        echo "[RECREATE] Starting new containers..."
                        docker-compose up -d
                        sleep 20
                        docker-compose ps
                    """
                }
                carbonSnapshot(phase: 'after', infraMultiplier: '1.0', downtimeSeconds: '20')
            }
        }

        stage('Smoke Test (Local)') {
            when { expression { !params.DRY_RUN && appAffected() } }
            steps {
                sh 'curl -sf http://localhost:8080/health && echo "SMOKE TEST PASSED" || exit 1'
            }
        }
    }

    post {
        success {
            script {
                if (appAffected() && !params.DRY_RUN) {
                    def img = "${DOCKER_IMAGE}:${DOCKER_TAG}"
                    notifyEnd(status: 'SUCCESS', image: img)
                    echo "Deployment complete - Strategy: ${env.DEPLOY_STRATEGY} | Carbon: ${env.CARBON_RATING}"
                }
            }
            dir(env.WORK_DIR) {
                sh "echo ${env.COMMIT_SHA} > .last_built_commit"
            }
            echo "Build SUCCESSFUL — Build #${BUILD_NUMBER}"
        }

        failure {
            script {
                if (env.DEPLOY_STRATEGY == 'canary' && appAffected()) {
                    sh "docker rm -f ${CANARY_CONTAINER} || true && echo '[CANARY] Rolled back'"
                }
                if (appAffected() && !params.DRY_RUN) {
                    notifyEnd(status: 'FAILURE')
                }
            }
            echo "Build FAILED — Build #${BUILD_NUMBER}"
        }

        always {
            // Dashboard metrics for the build-optimization side (Component: Beliver's dashboard)
            dir(env.WORK_DIR) {
                script {
                    def totalDuration = (System.currentTimeMillis() - env.PIPELINE_START.toLong()) / 1000.0

                    def currentStatus = currentBuild.currentResult ?: 'UNKNOWN'
                    if (env.IS_RESCHEDULED == 'true') {
                        currentStatus = 'RESCHEDULED'
                    }

                    def cleanCommitMsg = (env.COMMIT_MSG ?: '').replaceAll('"', '\\\\"')
                    def jsonPayload = """{
                        "job_name": "${env.JOB_NAME}",
                        "build_number": "${env.BUILD_NUMBER}",
                        "pipeline_type": "optimized_build_and_deploy",
                        "commit_sha": "${env.COMMIT_SHA ?: ''}",
                        "commit_message": "${cleanCommitMsg}",
                        "status": "${currentStatus}",
                        "total_duration_s": ${totalDuration},
                        "build_duration_s": ${env.BUILD_DURATION ?: 'null'},
                        "test_duration_s": ${env.TEST_DURATION ?: 'null'},
                        "docker_duration_s": ${env.DOCKER_BUILD_DURATION ?: 'null'},
                        "optimizer_duration_s": ${env.OPTIMIZER_DURATION ?: 'null'},
                        "modules_built": "${env.AFFECTED_MODULES ?: ''}",
                        "modules_tested": "${env.AFFECTED_MODULES ?: ''}",
                        "tests_executed": ${env.TESTS_EXECUTED ?: 0},
                        "tests_skipped": ${env.TESTS_SKIPPED ?: 0},
                        "module_details": "${env.MODULE_DETAILS ?: ''}",
                        "build_command": "${(env.MAVEN_BUILD_COMMANDS ?: '').replaceAll('"', '\\\\"')}",
                        "test_command": "${(env.MAVEN_TEST_COMMANDS ?: '').replaceAll('"', '\\\\"')}",
                        "carbon_intensity": ${env.CARBON_INTENSITY ?: 'null'},
                        "green_probability": ${env.GREEN_PROBABILITY ?: 'null'},
                        "scheduling_action": "${env.SCHEDULING_ACTION ?: ''}",
                        "scheduling_engine": "${env.SCHEDULING_ENGINE ?: ''}",
                        "carbon_history": ${env.CARBON_HISTORY ?: '[]'},
                        "carbon_forecast": ${env.CARBON_FORECAST ?: '[]'},
                        "deploy_strategy": "${env.DEPLOY_STRATEGY ?: ''}"
                    }"""

                    writeFile file: 'dashboard_payload.json', text: jsonPayload

                    sh """
                        curl -s -X POST ${DASHBOARD_URL}/api/builds \
                            -H "Content-Type: application/json" \
                            -d @dashboard_payload.json || \
                        curl -s -X POST http://localhost:5003/api/builds \
                            -H "Content-Type: application/json" \
                            -d @dashboard_payload.json || \
                        curl -s -X POST http://127.0.0.1:5003/api/builds \
                            -H "Content-Type: application/json" \
                            -d @dashboard_payload.json || \
                        curl -s -X POST http://172.17.0.1:5003/api/builds \
                            -H "Content-Type: application/json" \
                            -d @dashboard_payload.json || \
                        echo "Failed to send metrics to dashboard."
                    """
                }

                sh "docker rmi ${DOCKER_IMAGE}:${DOCKER_TAG} || true"
                sh "docker rmi ${DOCKER_IMAGE}:canary || true"
                sh "docker image prune -f || true"
            }
        }
    }
}