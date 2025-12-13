import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: root
    visible: true
    width: 480
    height: 320
    title: "SHATROX AI Robot"
    color: "#0a0a0a"
    
    // Helper function to add laugh message to log
    function addLaughToLog() {
        var xhr = new XMLHttpRequest()
        xhr.open("GET", "file://" + logMonitor.logFile, false)
        var currentLog = ""
        try {
            xhr.send()
            if (xhr.status === 200 || xhr.status === 0) {
                currentLog = xhr.responseText
            }
        } catch(e) {}
        
        // Append laugh message  
        var laughMsg = "\n😄 HA HA HA HA HA! 😄\n"
        var newLog = currentLog + laughMsg
        
        // Write back to log file
        var writeXhr = new XMLHttpRequest()
        writeXhr.open("PUT", "file://" + logMonitor.logFile, false)
        try {
            writeXhr.send(newLog)
        } catch(e) {
            console.log("Could not write laugh to log:", e)
        }
    }
    
    // Touch monitor (ADS7846 driver workaround - monitors IRQ count)
    Timer {
        id: touchMonitor
        interval: 100
        running: true
        repeat: true
        
        property string touchFile: "/tmp/shatrox-touch-trigger"
        property string lastTouch: ""
        
        onTriggered: {
            var content = fileReader.readFile(touchFile)
            if (content !== "" && content !== lastTouch) {
                lastTouch = content
                console.log("TOUCH DETECTED via IRQ monitor!")
                addLaughToLog()
                laughAnimation.start()
            }
        }
    }
    
    
    
    // Robot Face Layout - Free positioning
    Item {
        anchors.fill: parent
        
        // Eyes Row - at top
        Row {
            id: eyesRow
            anchors.top: parent.top
            anchors.topMargin: 5
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 180
            
            // Left Eye
            Rectangle {
                id: leftEye
                width: 70
                height: 70
                radius: 50
                color: "#1a1a1a"
                border.color: "#00ff00"
                border.width: 3
                
                Rectangle {
                    id: leftPupil
                    width: 20
                    height: 20
                    radius: 12
                    color: "#00ff00"
                    anchors.centerIn: parent
                    
                    SequentialAnimation on y {
                        running: true
                        loops: Animation.Infinite
                        NumberAnimation { to: leftEye.height * 0.4; duration: 2000 }
                        NumberAnimation { to: leftEye.height * 0.5; duration: 2000 }
                        NumberAnimation { to: leftEye.height * 0.6; duration: 2000 }
                        NumberAnimation { to: leftEye.height * 0.5; duration: 2000 }
                    }
                }
                
                // Blink eyelid
                Rectangle {
                    id: leftEyelid
                    width: parent.width
                    height: 0
                    color: "#0a0a0a"
                    anchors.top: parent.top
                }
                
                // Touch handler
                MouseArea {
                    anchors.fill: parent
                    z: 10
                    onClicked: {
                        console.log("Eye tapped - laughing!")
                        addLaughToLog()
                        laughAnimation.start()
                    }
                }
            }
            
            // Right Eye
            Rectangle {
                id: rightEye
                width: 70
                height: 70
                radius: 50
                color: "#1a1a1a"
                border.color: "#00ff00"
                border.width: 3
                
                Rectangle {
                    id: rightPupil
                    width: 20
                    height: 20
                    radius: 12
                    color: "#00ff00"
                    anchors.centerIn: parent
                    
                    SequentialAnimation on y {
                        running: true
                        loops: Animation.Infinite
                        NumberAnimation { to: rightEye.height * 0.4; duration: 2000 }
                        NumberAnimation { to: rightEye.height * 0.5; duration: 2000 }
                        NumberAnimation { to: rightEye.height * 0.6; duration: 2000 }
                        NumberAnimation { to: rightEye.height * 0.5; duration: 2000 }
                    }
                }
                
                // Blink eyelid
                Rectangle {
                    id: rightEyelid
                    width: parent.width
                    height: 0
                    color: "#0a0a0a"
                    anchors.top: parent.top
                }
                
                // Touch handler
                MouseArea {
                    anchors.fill: parent
                    z: 10
                    onClicked: {
                        console.log("Eye tapped - laughing!")
                        addLaughToLog()
                        laughAnimation.start()
                    }
                }
            }
        }
        
        // CPU Temperature Display (Nose) - BETWEEN eyes
        Rectangle {
            id: noseTemp
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: eyesRow.verticalCenter
            anchors.horizontalCenterOffset: -35
            width: 65
            height: 30
            radius: 6
            color: "#1a1a1a"
            border.color: cpuTempMonitor.tempColor
            border.width: 2
            
            Row {
                anchors.centerIn: parent
                spacing: 2
                
                Text {
                    text: Math.round(cpuTempMonitor.temperature) + "°C"
                    font.family: "Monospace"
                    font.pixelSize: 10
                    font.bold: true
                    color: cpuTempMonitor.tempColor
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
        
        // Speaker Volume Display - next to CPU temp
        Rectangle {
            id: volumeIndicator
            anchors.left: noseTemp.right
            anchors.leftMargin: 5
            anchors.verticalCenter: eyesRow.verticalCenter
            width: 65
            height: 30
            radius: 6
            color: "#1a1a1a"
            border.color: volumeMonitor.volumeColor
            border.width: 2
            
            Row {
                anchors.centerIn: parent
                spacing: 3
                
                Text {
                    text: "♪"
                    font.family: "Monospace"
                    font.pixelSize: 12
                    font.bold: true
                    color: volumeMonitor.volumeColor
                    anchors.verticalCenter: parent.verticalCenter
                }
                
                Text {
                    text: Math.round(volumeMonitor.volumePercent) + "%"
                    font.family: "Monospace"
                    font.pixelSize: 10
                    font.bold: true
                    color: volumeMonitor.volumeColor
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
        
        // Mouth (Text Display Area) - Now with MORE vertical space
        Rectangle {
            id: mouthArea
            anchors.top: eyesRow.bottom
            anchors.topMargin: 10
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 5
            anchors.rightMargin: 5
            radius: 8
            color: "#1a1a1a"
            border.color: "#00ff00"
            border.width: 3
            
            // Pulsing border when speaking
            SequentialAnimation on border.width {
                running: qaMonitor.hasNewContent
                loops: Animation.Infinite
                NumberAnimation { from: 3; to: 5; duration: 300 }
                NumberAnimation { from: 5; to: 3; duration: 300 }
            }
            
            ScrollView {
                id: scrollView
                anchors.fill: parent
                anchors.margins: 15
                clip: true
                
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                
                TextArea {
                    id: textDisplay
                    width: scrollView.width - 10
                    readOnly: true
                    wrapMode: TextArea.Wrap
                    selectByMouse: false
                    selectByKeyboard: false
                    
                    font.family: "Monospace"
                    font.pixelSize: 13
                    font.bold: false
                    color: "#00ff00"
                    
                    background: Rectangle {
                        color: "transparent"
                    }
                    
                    text: qaMonitor.qaContent
                    
                    // Auto-scroll to bottom when text changes
                    onTextChanged: {
                        Qt.callLater(function() {
                            scrollView.contentItem.contentY = scrollView.contentItem.contentHeight - scrollView.height
                        })
                    }
                }
            }
        }
    }
    
    // ============================================================
    // CAMERA PHOTO OVERLAY
    // ============================================================
    
    // Photo overlay background (full screen with transparency)
    Rectangle {
        id: photoOverlay
        anchors.fill: parent
        color: "#000000"
        opacity: 0
        visible: opacity > 0
        z: 100
        
        // Centered photo display
        Image {
            id: photoDisplay
            anchors.centerIn: parent
            width: 400
            height: 300
            fillMode: Image.PreserveAspectFit
            source: ""
            cache: false
            
            // Border around photo
            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: "#00ff00"
                border.width: 3
                radius: 4
            }
        }
        
        // Camera icon indicator
        Text {
            anchors.top: photoDisplay.bottom
            anchors.topMargin: 10
            anchors.horizontalCenter: parent.horizontalCenter
            text: "📷 Camera Capture"
            font.family: "Monospace"
            font.pixelSize: 14
            font.bold: true
            color: "#00ff00"
        }
        
        // Fade in animation
        NumberAnimation {
            id: photoFadeIn
            target: photoOverlay
            property: "opacity"
            from: 0
            to: 0.95
            duration: 300
            easing.type: Easing.InOutQuad
        }
        
        // Fade out animation
        NumberAnimation {
            id: photoFadeOut
            target: photoOverlay
            property: "opacity"
            from: 0.95
            to: 0
            duration: 500
            easing.type: Easing.InOutQuad
        }
        
        // Auto-hide timer (5 seconds)
        Timer {
            id: photoHideTimer
            interval: 5000
            running: false
            repeat: false
            onTriggered: photoFadeOut.start()
        }
    }
    
    // Photo monitor - detects new photos via trigger file
    Timer {
        id: photoMonitor
        interval: 200
        running: true
        repeat: true
        
        property string triggerFile: "/tmp/shatrox-photo-trigger"
        property string lastTrigger: ""
        property string photoFile: "/tmp/shatrox-latest-photo.jpg"
        
        onTriggered: {
            var trigger = fileReader.readFile(triggerFile)
            if (trigger !== "" && trigger !== lastTrigger) {
                lastTrigger = trigger
                console.log("New photo detected! Showing overlay...")
                
                // Force reload the image
                photoDisplay.source = ""
                photoDisplay.source = "file://" + photoFile
                
                // Show overlay with animation
                photoFadeIn.start()
                photoHideTimer.restart()
            }
        }
    }
    

    // Random blink timer
    Timer {
        id: blinkTimer
        interval: 3000 + Math.random() * 2000
        running: true
        repeat: true
        
        onTriggered: {
            blinkAnimation.start()
            interval = 3000 + Math.random() * 2000  // Randomize next blink
        }
    }
    
    // Blink animation
    SequentialAnimation {
        id: blinkAnimation
        
        ParallelAnimation {
            NumberAnimation {
                target: leftEyelid
                property: "height"
                to: leftEye.height
                duration: 100
            }
            NumberAnimation {
                target: rightEyelid
                property: "height"
                to: rightEye.height
                duration: 100
            }
        }
        
        PauseAnimation { duration: 80 }
        
        ParallelAnimation {
            NumberAnimation {
                target: leftEyelid
                property: "height"
                to: 0
                duration: 100
            }
            NumberAnimation {
                target: rightEyelid
                property: "height"
                to: 0
                duration: 100
            }
        }
    }
    
    // Laugh animation (quick repeated blinks)
    SequentialAnimation {
        id: laughAnimation
        
        // Play laugh sound at start
        ScriptAction {
            script: {
                // Trigger laugh sound using speak command
                var component = Qt.createQmlObject('import QtQuick 2.15; import Qt.labs.platform 1.1; Process { onFinished: destroy() }',
                                                   root, "laughProcess")
                // Use Piper TTS to say "ha ha ha ha" with expression
                laughSound.playLaugh()
            }
        }
        
        // Three quick blinks
        ParallelAnimation {
            NumberAnimation { target: leftEyelid; property: "height"; to: leftEye.height; duration: 80 }
            NumberAnimation { target: rightEyelid; property: "height"; to: rightEye.height; duration: 80 }
        }
        PauseAnimation { duration: 60 }
        ParallelAnimation {
            NumberAnimation { target: leftEyelid; property: "height"; to: 0; duration: 80 }
            NumberAnimation { target: rightEyelid; property: "height"; to: 0; duration: 80 }
        }
        PauseAnimation { duration: 100 }
        
        ParallelAnimation {
            NumberAnimation { target: leftEyelid; property: "height"; to: leftEye.height; duration: 80 }
            NumberAnimation { target: rightEyelid; property: "height"; to: rightEye.height; duration: 80 }
        }
        PauseAnimation { duration: 60 }
        ParallelAnimation {
            NumberAnimation { target: leftEyelid; property: "height"; to: 0; duration: 80 }
            NumberAnimation { target: rightEyelid; property: "height"; to: 0; duration: 80 }
        }
        PauseAnimation { duration: 100 }
        
        ParallelAnimation {
            NumberAnimation { target: leftEyelid; property: "height"; to: leftEye.height; duration: 80 }
            NumberAnimation { target: rightEyelid; property: "height"; to: rightEye.height; duration: 80 }
        }
        PauseAnimation { duration: 60 }
        ParallelAnimation {
            NumberAnimation { target: leftEyelid; property: "height"; to: 0; duration: 80 }
            NumberAnimation { target: rightEyelid; property: "height"; to: 0; duration: 80 }
        }
    }
    
    // Laugh sound handler
    QtObject {
        id: laughSound
        
        function playLaugh() {
            console.log("Triggering laugh sound...")
            // Write trigger file - a monitor script can watch for this
            var xhr = new XMLHttpRequest()
            xhr.open("PUT", "file:///tmp/shatrox-laugh-trigger", false)
            try {
                xhr.send(new Date().toString() + "\\n")
            } catch(e) {
                console.log("Could not write laugh trigger:", e)
            }
        }
    }
    
    
    // Clean Q&A monitor (for mouth display)
    Timer {
        id: qaMonitor
        interval: 500
        running: true
        repeat: true
        
        property string qaContent: "╔════════════════════════════╗\n║  SHATROX AI Robot Ready  ║\n╚════════════════════════════╝\n\nSay 'Hey Jarvis' to activate\nPress K1 to talk\nPress K3 for camera"
        property string previousContent: ""
        property string qaFile: "/tmp/ai-qa-display.txt"
        property bool hasNewContent: false
        
        onTriggered: {
            var content = fileReader.readFile(qaFile)
            if (content !== "" && content !== qaContent) {
                // Detect new content
                hasNewContent = (content.length > previousContent.length)
                previousContent = qaContent
                qaContent = content
                
                // Reset new content flag after animation
                if (hasNewContent) {
                    newContentTimer.restart()
                }
            }
        }
    }
    
    // Timer to reset new content flag
    Timer {
        id: newContentTimer
        interval: 2000
        onTriggered: qaMonitor.hasNewContent = false
    }
    

    
    // Temperature monitoring timer
    Timer {
        id: cpuTempMonitor
        interval: 500
        running: true
        repeat: true
        
        property real temperature: 0.0
        property string tempColor: "#00ff00"
        property bool fanActive: false
        property string thermalFile: "/sys/class/thermal/thermal_zone0/temp"
        
        function updateColor() {
            if (temperature < 50) {
                tempColor = "#00ff00"
            } else if (temperature < 60) {
                tempColor = "#ffff00"
            } else if (temperature < 70) {
                tempColor = "#ff8800"
            } else {
                tempColor = "#ff0000"
            }
            fanActive = (temperature >= 40)
        }
        
        onTriggered: {
            var content = fileReader.readFile(thermalFile)
            if (content !== "") {
                var tempMilliC = parseInt(content.trim())
                if (!isNaN(tempMilliC)) {
                    temperature = tempMilliC / 1000.0
                    updateColor()
                }
            }
        }
    }
    
    // Speaker Volume monitoring timer
    Timer {
        id: volumeMonitor
        interval: 500
        running: true
        repeat: true
        
        property real volumePercent: 0.0
        property string volumeColor: "#00ff00"
        property string volumeFile: "/tmp/shatrox-volume-status"
        
        function updateColor() {
            if (volumePercent <= 50) {
                volumeColor = "#00ff00"  // Green
            } else if (volumePercent <= 75) {
                volumeColor = "#ffff00"  // Yellow
            } else if (volumePercent <= 90) {
                volumeColor = "#ff8800"  // Orange
            } else {
                volumeColor = "#ff0000"  // Red
            }
        }
        
        onTriggered: {
            var content = fileReader.readFile(volumeFile)
            if (content !== "") {
                // Parse volume percentage from file
                // Expected format: "49" (just the percentage number)
                var percent = parseInt(content.trim())
                if (!isNaN(percent)) {
                    volumePercent = percent
                    updateColor()
                }
            }
        }
    }
    
    // File reader helper
    QtObject {
        id: fileReader
        
        function readFile(filePath) {
            var xhr = new XMLHttpRequest()
            xhr.open("GET", "file://" + filePath, false)
            try {
                xhr.send()
                if (xhr.status === 200 || xhr.status === 0) {
                    return xhr.responseText
                }
            } catch (e) {
                console.log("Error reading file:", e)
            }
            return ""
        }
    }
    
    Component.onCompleted: {
        console.log("SHATROX Robot Face Display Started")
        console.log("Monitoring:", qaMonitor.qaFile)
        console.log("Temperature sensor:", cpuTempMonitor.thermalFile)
        console.log("Volume status:", volumeMonitor.volumeFile)
        console.log("Photo trigger:", photoMonitor.triggerFile)
    }
}
