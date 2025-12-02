document.addEventListener("alpine:init", () => {
  Alpine.data("mathMonkey", (initialLevel, initialMMR) => ({
    userLevel: initialLevel,
    userMMR: initialMMR,

    profileData: null,
    showLevelUp: false,

    scene: "menu",
    questions: [],
    currentQuestionIndex: 0,

    time: 60,
    totalTimePlayed: 0,
    score: 0,
    streak: 0,
    wrongStreak: 0,
    highestStreak: 0,
    correctCount: 0,
    totalAnswered: 0,

    leaderboard: [],

    theme: localStorage.getItem("mm_theme") || "cupcake",
    isMuted: localStorage.getItem("mm_muted") === "true",
    currentBGM: null,

    sounds: {
      click: new Audio("/static/sounds/click.mp3"),
      pop: new Audio("/static/sounds/pop.mp3"),
      correct: new Audio("/static/sounds/correct.mp3"),
      incorrect: new Audio("/static/sounds/incorrect.mp3"),
      gameover: new Audio("/static/sounds/gameover.mp3"),
      win: new Audio("/static/sounds/win.mp3"),

      bg_menu: new Audio("/static/sounds/bg3.mp3"),
      bg_fast: new Audio("/static/sounds/bg1.mp3"),
      bg_zen: new Audio("/static/sounds/bg2.mp3"),
    },

    gameConfig: {
      mode: "timetrial",
      difficulty: "medium",
      topics: ["mixed"],
      form: [],
    },

    timerInterval: null,
    isLoading: false,
    feedback: { show: false, isCorrect: true },

    get currentQuestion() {
      return (
        this.questions[this.currentQuestionIndex] || {
          text: "Loading...",
          choices: [],
        }
      );
    },

    get formattedTime() {
      const m = Math.floor(this.time / 60);
      const s = this.time % 60;
      return `${m}:${s < 10 ? "0" : ""}${s}`;
    },

    async startQuickPlay() {
      this.playSFX("click");
      this.playBGM("bg_fast");

      this.gameConfig = {
        mode: "timetrial",
        difficulty: "medium",
        topics: ["mixed"],
        form: ["mixed"],
      };

      this.resetGameStats(60);
      this.isLoading = true;
      await this.fetchQuestions(10);
      this.isLoading = false;
      this.scene = "game";
      this.startGameLoop();
    },

    async fetchQuestions(count = 10) {
      try {
        const topicParam = Array.isArray(this.gameConfig.topics)
          ? this.gameConfig.topics.join(",")
          : this.gameConfig.topics;
        const formParam = Array.isArray(this.gameConfig.form)
          ? this.gameConfig.form.join(",")
          : this.gameConfig.form;

        const params = new URLSearchParams({
          difficulty: this.gameConfig.difficulty,
          topics: topicParam,
          form: formParam,
          count: count,
        });

        const response = await fetch(`/api/questions/?${params.toString()}`);
        const newQuestions = await response.json();
        this.questions = [...this.questions, ...newQuestions];
      } catch (error) {
        console.error("Error fetching questions:", error);
      }
    },

    async startCustomGame() {
      if (this.gameConfig.topics.length === 0) return;
      this.playSFX("click");
      if (this.gameConfig.mode === "zen") {
        this.playBGM("bg_zen");
      } else {
        this.playBGM("bg_fast");
      }
      const startTime = this.gameConfig.mode === "zen" ? 0 : 60;
      this.resetGameStats(startTime);
      this.isLoading = true;
      await this.fetchQuestions(10);
      this.isLoading = false;
      this.scene = "game";
      this.startGameLoop();
    },

    resetGameStats(startTime) {
      this.score = 0;
      this.time = startTime;
      this.totalTimePlayed = 0;
      this.streak = 0;
      this.wrongStreak = 0;
      this.highestStreak = 0;
      this.correctCount = 0;
      this.totalAnswered = 0;
      this.currentQuestionIndex = 0;
      this.questions = [];
    },

    startGameLoop() {
      if (this.timerInterval) clearInterval(this.timerInterval);

      this.timerInterval = setInterval(() => {
        this.totalTimePlayed++;

        if (this.gameConfig.mode === "timetrial") {
          this.time--;
          if (this.time <= 0) {
            this.time = 0;
            this.endGame();
          }
        } else {
          this.time++;
        }
      }, 1000);
    },

    handleAnswer(choice) {
      if (this.gameConfig.mode === "timetrial" && this.time <= 0) return;

      const q = this.currentQuestion;
      const isCorrect = choice === q.answer;
      this.totalAnswered++;

      if (isCorrect) {
        this.playSFX("correct");
        if (this.gameConfig.mode === "timetrial") {
          this.time += 3;
          this.score += 100 + this.streak * 10;

          this.streak++;
          if (this.streak > this.highestStreak)
            this.highestStreak = this.streak;
          if (this.streak === 5) this.adjustDifficulty("up");
        } else {
          this.score += 10;
          this.streak++;
          if (this.streak > this.highestStreak)
            this.highestStreak = this.streak;
        }

        this.wrongStreak = 0;
        this.correctCount++;
      } else {
        this.playSFX("incorrect");
        if (this.gameConfig.mode === "timetrial") {
          this.time -= 5;
          if (this.time < 0) this.time = 0;

          this.streak = 0;
          this.wrongStreak++;
          if (this.wrongStreak === 3) this.adjustDifficulty("down");
        } else {
          this.streak = 0;
        }
      }
      this.feedback = { show: true, isCorrect: isCorrect };
      setTimeout(() => {
        this.feedback.show = false;
      }, 500);
      this.currentQuestionIndex++;
      if (this.questions.length - this.currentQuestionIndex < 5) {
        this.fetchQuestions(10);
      }
    },

    adjustDifficulty(direction) {
      const levels = ["easy", "medium", "hard"];
      let idx = levels.indexOf(this.gameConfig.difficulty);

      if (direction === "up" && idx < 2) {
        this.gameConfig.difficulty = levels[idx + 1];
        this.streak = 0;
      } else if (direction === "down" && idx > 0) {
        this.gameConfig.difficulty = levels[idx - 1];
        this.wrongStreak = 0;
      }
    },

    async endGame() {
      this.currentBGM.pause();

      clearInterval(this.timerInterval);

      this.scene = "results";

      const payload = {
        mode: this.gameConfig.mode,
        score: this.score,
        total_questions: this.totalAnswered,
        correct_answers: this.correctCount,
        duration: this.totalTimePlayed,
        final_difficulty: this.gameConfig.difficulty,
        topics: this.gameConfig.topics,
        highest_streak: this.highestStreak,
      };

      const csrfToken = document
        .querySelector('meta[name="csrf-token"]')
        .getAttribute("content");

      try {
        const response = await fetch("/api/submit/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (result.status === "success") {
          this.userMMR = result.new_mmr;
          this.userLevel = result.new_level;
          if (result.leveled_up) {
            this.playSFX("win");
            this.showLevelUp = true;
          } else {
            this.playSFX("gameover");
          }
        }
      } catch (err) {
        console.error("Failed to save score", err);
      }
    },

    async getLeaderboard() {
      this.isLoading = true;
      this.scene = "leaderboard";

      try {
        const response = await fetch("/api/leaderboard/");
        this.leaderboard = await response.json();
      } catch (error) {
        console.error("Error fetching leaderbard:", error);
      } finally {
        this.isLoading = false;
      }
    },

    async openProfile() {
      this.playSFX("click");
      this.scene = "profile";
      this.isLoading = true;

      try {
        const response = await fetch("/api/profile/");
        this.profileData = await response.json();
      } catch (error) {
        console.error("Error loading profile:", error);
      } finally {
        this.isLoading = false;
      }
    },

    toggleMute() {
      this.isMuted = !this.isMuted;
      localStorage.setItem("mm_muted", this.isMuted);
      this.updateVolume();
    },

    updateVolume() {
      const volume = this.isMuted ? 0 : 0.5;

      Object.values(this.sounds).forEach((audio) => {
        audio.volume = volume;
      });
    },

    playSFX(key) {
      if (this.isMuted) return;

      const sound = this.sounds[key];
      if (sound) {
        const clone = sound.cloneNode();
        clone.volume = sound.volume;
        clone.play().catch((e) => console.warn("SFX play failed:", key, e));
      }
    },

    playBGM(key) {
      const newTrack = this.sounds[key];
      if (this.currentBGM === newTrack && !this.currentBGM.paused) return;

      if (this.currentBGM) {
        this.currentBGM.pause();
        this.currentBGM.currentTime = 0;
      }

      if (newTrack) {
        this.currentBGM = newTrack;
        newTrack.play().catch((e) => console.log("Audio play failed:", e));
      }
    },

    toggleTheme() {
      this.theme = this.theme === "cupcake" ? "forest" : "cupcake";
      document.documentElement.setAttribute("data-theme", this.theme);
      localStorage.setItem("mm_theme", this.theme);
      this.playSFX("pop");
    },

    init() {
      this.sounds.bg_menu.loop = true;
      this.sounds.bg_fast.loop = true;
      this.sounds.bg_zen.loop = true;
      this.updateVolume();
      this.playBGM("bg_menu");

      const unlockAudio = () => {
        if (this.currentBGM && this.currentBGM.paused) {
          this.currentBGM
            .play()
            .catch((e) => console.log("Retry play failed:", e));
        }
        document.removeEventListener("click", unlockAudio);
        document.removeEventListener("keydown", unlockAudio);
      };

      document.addEventListener("click", unlockAudio);
      document.addEventListener("keydown", unlockAudio);

      this.$watch("scene", (val) => {
        if (val === "menu") {
          this.playBGM("bg_menu");
        }
      });
    },
  }));
});
