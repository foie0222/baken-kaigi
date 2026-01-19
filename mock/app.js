// App State
const state = {
    isLoggedIn: false,
    currentPage: 'races',
    selectedRace: null,
    betData: {
        type: '馬連',
        numbers: '',
        amount: 1000
    },
    selectedHorses: [],  // 選択された馬番の配列
    userLimit: 30000,
    currentLoss: 27000,
    chatMessages: [],
    cart: []  // { race, type, numbers, amount } の配列
};

// Sample Data
const races = [
    { id: 1, number: '11R', name: '天皇賞（春）', time: '15:40', course: '芝3200m', condition: '良', venue: '東京' },
    { id: 2, number: '10R', name: '駒草特別', time: '15:00', course: '芝1800m', condition: '良', venue: '東京' },
    { id: 3, number: '9R', name: '青嵐賞', time: '14:25', course: 'ダ1400m', condition: '良', venue: '東京' },
    { id: 4, number: '12R', name: '立夏特別', time: '16:20', course: '芝1400m', condition: '良', venue: '東京' },
];

const horses = [
    { number: 1, name: 'ディープボンド', jockey: '和田竜二', odds: 5.2, popularity: 2, color: '#c41e3a' },
    { number: 2, name: 'テーオーロイヤル', jockey: '菱田裕二', odds: 8.5, popularity: 4, color: '#000000' },
    { number: 3, name: 'タイトルホルダー', jockey: '横山武史', odds: 3.1, popularity: 1, color: '#0066cc' },
    { number: 4, name: 'ジャスティンパレス', jockey: 'C.ルメール', odds: 6.8, popularity: 3, color: '#ffcc00' },
    { number: 5, name: 'シルヴァーソニック', jockey: '松山弘平', odds: 15.2, popularity: 6, color: '#008000' },
    { number: 6, name: 'ブレークアップ', jockey: '川田将雅', odds: 12.4, popularity: 5, color: '#ff6600' },
    { number: 7, name: 'アスクビクターモア', jockey: '田辺裕信', odds: 18.6, popularity: 7, color: '#9933cc' },
    { number: 8, name: 'ヒートオンビート', jockey: '坂井瑠星', odds: 35.8, popularity: 8, color: '#ff69b4' },
];

const history = [
    { date: '1/18', race: '中山11R 皐月賞', bet: '馬連 3-7', amount: 2000, result: -2000 },
    { date: '1/18', race: '京都10R 桜花賞', bet: '単勝 5', amount: 1000, result: 3500 },
    { date: '1/17', race: '東京12R 青葉賞', bet: '三連複 2-5-8', amount: 1500, result: -1500 },
    { date: '1/14', race: '中山9R 若葉S', bet: '馬連 1-4', amount: 1000, result: -1000 },
    { date: '1/14', race: '阪神11R 大阪杯', bet: '単勝 3', amount: 3000, result: 8400 },
];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    renderPage('races');
    initLoginButton();
});

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            const page = item.dataset.page;
            state.currentPage = page;
            state.selectedRace = null;
            renderPage(page);
        });
    });
}

function initLoginButton() {
    document.getElementById('login-btn').addEventListener('click', () => {
        if (state.isLoggedIn) {
            state.isLoggedIn = false;
            updateLoginState();
        } else {
            document.getElementById('login-modal').classList.remove('hidden');
        }
    });
}

function doLogin() {
    state.isLoggedIn = true;
    closeModal();
    updateLoginState();
    renderPage(state.currentPage);
}

function closeModal() {
    document.getElementById('login-modal').classList.add('hidden');
}

function updateLoginState() {
    const loginBtn = document.getElementById('login-btn');
    const alertBanner = document.getElementById('alert-banner');
    const headerActions = document.querySelector('.header-actions');

    if (state.isLoggedIn) {
        // ログインボタンをユーザー情報に置き換え
        if (loginBtn) {
            loginBtn.outerHTML = `
                <div class="user-info">
                    <span class="user-balance">¥50,000</span>
                    <button class="login-btn" id="login-btn" onclick="doLogout()">ログアウト</button>
                </div>
            `;
        }
        if (state.currentLoss >= state.userLimit * 0.8) {
            alertBanner.classList.remove('hidden');
        }
    } else {
        // ユーザー情報をログインボタンに戻す
        const userInfo = document.querySelector('.user-info');
        if (userInfo) {
            userInfo.outerHTML = `<button class="login-btn" id="login-btn">ログイン</button>`;
            initLoginButton();
        }
        alertBanner.classList.add('hidden');
    }
}

function doLogout() {
    state.isLoggedIn = false;
    location.reload();
}

function renderPage(page) {
    const main = document.getElementById('main-content');

    switch(page) {
        case 'races':
            if (state.selectedRace) {
                renderRaceDetail();
            } else {
                renderRaceList();
            }
            break;
        case 'dashboard':
            renderDashboard();
            break;
        case 'history':
            renderHistory();
            break;
        case 'settings':
            renderSettings();
            break;
    }
}

function renderRaceList() {
    const main = document.getElementById('main-content');
    main.innerHTML = `
        <div class="fade-in">
            <div class="race-date-selector">
                <button class="date-btn active">今日 1/18</button>
                <button class="date-btn">明日 1/19</button>
                <button class="date-btn">1/25 (土)</button>
                <button class="date-btn">1/26 (日)</button>
            </div>

            <div class="venue-tabs">
                <button class="venue-tab active">東京</button>
                <button class="venue-tab">中山</button>
                <button class="venue-tab">京都</button>
            </div>

            <p class="section-title">本日のレース</p>

            ${races.map(race => `
                <div class="race-card" onclick="selectRace(${race.id})">
                    <div class="race-header">
                        <span class="race-number">${race.number}</span>
                        <span class="race-time">${race.time} 発走</span>
                    </div>
                    <div class="race-name">${race.name}</div>
                    <div class="race-info">
                        <span>${race.course}</span>
                        <span>馬場: ${race.condition}</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function selectRace(id) {
    state.selectedRace = races.find(r => r.id === id);
    renderRaceDetail();
}

function renderRaceDetail() {
    const race = state.selectedRace;
    const main = document.getElementById('main-content');

    main.innerHTML = `
        <div class="fade-in">
            <button class="back-btn" onclick="goBack()">← レース一覧に戻る</button>

            <div class="race-detail-header">
                <span class="race-number">${race.venue} ${race.number}</span>
                <div class="race-name">${race.name}</div>
                <div class="race-conditions">
                    <span class="condition-tag">${race.course}</span>
                    <span class="condition-tag">馬場: ${race.condition}</span>
                    <span class="condition-tag">${race.time} 発走</span>
                </div>
            </div>

            <div class="horse-list">
                <div class="horse-list-header">
                    <span></span>
                    <span>馬番</span>
                    <span>馬名</span>
                    <span>オッズ</span>
                </div>
                ${horses.map(horse => `
                    <div class="horse-item ${state.selectedHorses.includes(horse.number) ? 'selected' : ''}"
                         onclick="toggleHorse(${horse.number})">
                        <div class="horse-checkbox">
                            <input type="checkbox"
                                   ${state.selectedHorses.includes(horse.number) ? 'checked' : ''}
                                   onclick="event.stopPropagation(); toggleHorse(${horse.number})">
                        </div>
                        <div class="horse-number" style="background: ${horse.color}">${horse.number}</div>
                        <div class="horse-info">
                            <div class="horse-name">${horse.name}</div>
                            <div class="horse-jockey">${horse.jockey}</div>
                        </div>
                        <div class="horse-odds">${horse.odds}</div>
                    </div>
                `).join('')}
            </div>

            <div class="bet-section">
                <h3>🎫 買い目を入力</h3>

                <div class="bet-type-selector">
                    ${['単勝', '複勝', '馬連', '馬単', '三連複', '三連単'].map(type => `
                        <button class="bet-type-btn ${state.betData.type === type ? 'active' : ''}"
                                onclick="selectBetType('${type}')">${type}</button>
                    `).join('')}
                </div>

                <div class="bet-input-group">
                    <label>選択した馬番 ${getRequiredHorsesHint()}</label>
                    <div class="selected-horses-display">
                        ${state.selectedHorses.length > 0 ? `
                            <span class="selected-numbers">${state.selectedHorses.sort((a,b) => a-b).join(' - ')}</span>
                            <button class="clear-selection-btn" onclick="clearHorseSelection()">クリア</button>
                        ` : `
                            <span class="no-selection">上のリストから馬を選択してください</span>
                        `}
                    </div>
                    ${!isValidHorseSelection() && state.selectedHorses.length > 0 ? `
                        <div class="selection-error">${getSelectionErrorMessage()}</div>
                    ` : ''}
                </div>

                <div class="bet-input-group">
                    <label>金額</label>
                    <div class="amount-input-wrapper">
                        <span class="currency-symbol">¥</span>
                        <input type="number" class="amount-input" id="bet-amount"
                               value="${state.betData.amount}"
                               onchange="updateBetAmount(this.value)">
                    </div>
                    <div class="amount-presets">
                        <button class="preset-btn" onclick="setAmount(100)">¥100</button>
                        <button class="preset-btn" onclick="setAmount(500)">¥500</button>
                        <button class="preset-btn" onclick="setAmount(1000)">¥1,000</button>
                        <button class="preset-btn" onclick="setAmount(5000)">¥5,000</button>
                    </div>
                </div>

                <button class="ai-consult-btn" onclick="addToCart()" ${!isValidHorseSelection() ? 'disabled' : ''}>
                    🛒 カートに追加
                </button>

                ${state.cart.length > 0 ? `
                    <button class="btn-secondary" style="margin-top: 12px; width: 100%;" onclick="showCart()">
                        カートを確認する（${state.cart.length}件）
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}

function goBack() {
    state.selectedRace = null;
    state.chatMessages = [];
    state.selectedHorses = [];
    renderPage('races');
}

function selectBetType(type) {
    state.betData.type = type;
    // 券種変更時に選択をリセットしない（ユーザーの利便性のため）
    renderRaceDetail();
}

function toggleHorse(number) {
    const index = state.selectedHorses.indexOf(number);
    if (index === -1) {
        state.selectedHorses.push(number);
    } else {
        state.selectedHorses.splice(index, 1);
    }
    renderRaceDetail();
}

function clearHorseSelection() {
    state.selectedHorses = [];
    renderRaceDetail();
}

function getRequiredHorsesHint() {
    const type = state.betData.type;
    switch(type) {
        case '単勝':
        case '複勝':
            return '（1頭選択）';
        case '馬連':
        case '馬単':
            return '（2頭選択）';
        case '三連複':
        case '三連単':
            return '（3頭選択）';
        default:
            return '';
    }
}

function getRequiredHorseCount() {
    const type = state.betData.type;
    switch(type) {
        case '単勝':
        case '複勝':
            return 1;
        case '馬連':
        case '馬単':
            return 2;
        case '三連複':
        case '三連単':
            return 3;
        default:
            return 1;
    }
}

function isValidHorseSelection() {
    return state.selectedHorses.length === getRequiredHorseCount();
}

function getSelectionErrorMessage() {
    const required = getRequiredHorseCount();
    const current = state.selectedHorses.length;
    if (current < required) {
        return `あと${required - current}頭選択してください`;
    } else if (current > required) {
        return `${current - required}頭多く選択されています`;
    }
    return '';
}

function updateBetNumbers(value) {
    state.betData.numbers = value;
}

function updateBetAmount(value) {
    state.betData.amount = parseInt(value) || 0;
}

function setAmount(amount) {
    state.betData.amount = amount;
    document.getElementById('bet-amount').value = amount;
}

function startAIConsult() {
    if (!state.betData.numbers) {
        alert('馬番を入力してください');
        return;
    }

    state.chatMessages = [
        { type: 'ai', text: `${state.betData.type} ${state.betData.numbers} で ¥${state.betData.amount.toLocaleString()} ですね。\n\nこの馬を選んだ理由を教えてください。` }
    ];

    renderAIChat();
}

function renderAIChat() {
    const main = document.getElementById('main-content');
    const race = state.selectedRace;
    const remainingLimit = state.userLimit - state.currentLoss;
    const isOverLimit = state.betData.amount > remainingLimit && state.isLoggedIn;

    main.innerHTML = `
        <div class="fade-in">
            <button class="back-btn" onclick="goBackToDetail()">← 買い目入力に戻る</button>

            <div class="ai-chat-container">
                <div class="ai-chat-header">
                    <div class="ai-avatar">🤖</div>
                    <div class="ai-chat-header-text">
                        <h3>馬券会議 AI</h3>
                        <p>立ち止まって、考えましょう</p>
                    </div>
                </div>

                <div class="chat-messages" id="chat-messages">
                    ${state.chatMessages.map(msg => `
                        <div class="chat-message ${msg.type}">
                            <div class="message-bubble">${msg.text.replace(/\n/g, '<br>')}</div>
                        </div>
                    `).join('')}
                </div>

                ${state.chatMessages.length === 1 ? `
                    <div class="quick-replies">
                        <button class="quick-reply-btn" onclick="selectReason('過去の成績が良い')">過去の成績</button>
                        <button class="quick-reply-btn" onclick="selectReason('騎手を信頼')">騎手</button>
                        <button class="quick-reply-btn" onclick="selectReason('オッズが魅力的')">オッズ</button>
                        <button class="quick-reply-btn" onclick="selectReason('直感で選んだ')">直感</button>
                    </div>
                ` : ''}

                ${state.chatMessages.length >= 2 ? `
                    <div class="data-feedback">
                        <div class="feedback-title">📊 データフィードバック</div>
                        <div class="feedback-item">
                            <span class="feedback-label">3番 タイトルホルダー</span>
                            <span class="feedback-value">前走1着 / 東京◎</span>
                        </div>
                        <div class="feedback-item">
                            <span class="feedback-label">7番 アスクビクターモア</span>
                            <span class="feedback-value">長距離実績△</span>
                        </div>
                        <div class="feedback-item">
                            <span class="feedback-label">${state.betData.type}オッズ</span>
                            <span class="feedback-value">12.5倍</span>
                        </div>
                        ${state.isLoggedIn ? `
                            <div class="feedback-item">
                                <span class="feedback-label">残り許容負け額</span>
                                <span class="feedback-value ${remainingLimit < 5000 ? 'warning' : ''}">
                                    ¥${remainingLimit.toLocaleString()}
                                </span>
                            </div>
                            <div class="feedback-item">
                                <span class="feedback-label">この賭けの最大損失</span>
                                <span class="feedback-value ${isOverLimit ? 'negative' : ''}">
                                    ¥${state.betData.amount.toLocaleString()}
                                    ${isOverLimit ? ' (限度額超過)' : ''}
                                </span>
                            </div>
                        ` : `
                            <div class="feedback-item">
                                <span class="feedback-label">平均的な掛け金</span>
                                <span class="feedback-value">¥1,000〜2,000</span>
                            </div>
                        `}
                    </div>

                    <div class="action-buttons">
                        ${state.isLoggedIn ? `
                            <button class="btn-primary" ${isOverLimit ? 'disabled' : ''} onclick="purchase()">
                                ${isOverLimit ? '限度額超過' : '購入する'}
                            </button>
                        ` : `
                            <button class="btn-primary" onclick="showLoginPrompt()">
                                ログインして購入
                            </button>
                        `}
                        <button class="btn-secondary" onclick="goBackToDetail()">やめておく</button>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function selectReason(reason) {
    state.chatMessages.push({ type: 'user', text: reason });
    state.chatMessages.push({
        type: 'ai',
        text: `なるほど、「${reason}」ですね。\n\n以下のデータを参考にしてください。最終判断はあなた自身で行いましょう。`
    });
    renderAIChat();
}

function goBackToDetail() {
    state.chatMessages = [];
    renderRaceDetail();
}

function purchase() {
    alert('馬券を購入しました！\n\n' + state.betData.type + ' ' + state.betData.numbers + '\n¥' + state.betData.amount.toLocaleString());
    state.currentLoss += state.betData.amount;
    goBack();
}

function showLoginPrompt() {
    document.getElementById('login-modal').classList.remove('hidden');
}

function renderDashboard() {
    const main = document.getElementById('main-content');
    const remainingLimit = state.userLimit - state.currentLoss;
    const usagePercent = (state.currentLoss / state.userLimit) * 100;

    if (!state.isLoggedIn) {
        main.innerHTML = `
            <div class="fade-in text-center" style="padding: 60px 20px;">
                <div style="font-size: 60px; margin-bottom: 20px;">📊</div>
                <h2 style="margin-bottom: 12px;">損益ダッシュボード</h2>
                <p style="color: #666; margin-bottom: 24px;">ログインすると、損益の管理や<br>負け額限度額の設定ができます。</p>
                <button class="btn-primary" onclick="document.getElementById('login-modal').classList.remove('hidden')">
                    ログインする
                </button>
            </div>
        `;
        return;
    }

    main.innerHTML = `
        <div class="fade-in">
            <div class="dashboard-summary">
                <div class="summary-label">今月の損益</div>
                <div class="summary-value negative">-¥${state.currentLoss.toLocaleString()}</div>

                <div class="limit-progress">
                    <div class="limit-progress-header">
                        <span>負け額限度額</span>
                        <span>¥${state.currentLoss.toLocaleString()} / ¥${state.userLimit.toLocaleString()}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill ${usagePercent >= 80 ? 'danger' : ''}" style="width: ${usagePercent}%"></div>
                    </div>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">残り許容負け額</div>
                    <div class="stat-value ${remainingLimit < 5000 ? 'negative' : ''}">¥${remainingLimit.toLocaleString()}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">勝率</div>
                    <div class="stat-value">23%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">賭け回数</div>
                    <div class="stat-value">18回</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">平均賭け金</div>
                    <div class="stat-value">¥1,500</div>
                </div>
            </div>

            <div class="period-tabs">
                <button class="period-tab active">日次</button>
                <button class="period-tab">週次</button>
                <button class="period-tab">月次</button>
                <button class="period-tab">累計</button>
            </div>

            <div style="background: white; border-radius: 12px; padding: 20px; text-align: center; color: #999;">
                <p>📈 損益推移グラフ</p>
                <p style="font-size: 12px; margin-top: 8px;">（実装時はChart.jsで描画）</p>
            </div>
        </div>
    `;
}

function renderHistory() {
    const main = document.getElementById('main-content');

    if (!state.isLoggedIn) {
        main.innerHTML = `
            <div class="fade-in text-center" style="padding: 60px 20px;">
                <div style="font-size: 60px; margin-bottom: 20px;">📋</div>
                <h2 style="margin-bottom: 12px;">賭け履歴</h2>
                <p style="color: #666; margin-bottom: 24px;">ログインすると、過去の賭け履歴を<br>確認できます。</p>
                <button class="btn-primary" onclick="document.getElementById('login-modal').classList.remove('hidden')">
                    ログインする
                </button>
            </div>
        `;
        return;
    }

    main.innerHTML = `
        <div class="fade-in">
            <p class="section-title">賭け履歴</p>

            ${history.map(item => `
                <div class="history-item">
                    <div class="history-header">
                        <span class="history-date">${item.date}</span>
                        <span class="history-result ${item.result >= 0 ? 'win' : 'lose'}">
                            ${item.result >= 0 ? '+' : ''}¥${item.result.toLocaleString()}
                        </span>
                    </div>
                    <div class="history-race">${item.race}</div>
                    <div class="history-bet">${item.bet} / ¥${item.amount.toLocaleString()}</div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderSettings() {
    const main = document.getElementById('main-content');

    main.innerHTML = `
        <div class="fade-in">
            ${state.isLoggedIn ? `
                <div class="settings-section">
                    <div class="settings-section-title">負け額限度額</div>
                    <div class="limit-setting">
                        <div class="limit-current">
                            <span class="limit-amount">¥${state.userLimit.toLocaleString()}</span>
                            <button class="limit-edit-btn" onclick="editLimit()">変更</button>
                        </div>
                        <p class="limit-note">
                            ※ 減額は即時反映されます<br>
                            ※ 増額には7日間の待機期間があります
                        </p>
                    </div>
                </div>

                <div class="settings-section">
                    <div class="settings-section-title">IPAT連携</div>
                    <div class="settings-item">
                        <span class="settings-item-label">JRA IPAT</span>
                        <span class="settings-item-value">
                            未連携
                            <span class="arrow">›</span>
                        </span>
                    </div>
                </div>

                <div class="settings-section">
                    <div class="settings-section-title">アカウント</div>
                    <div class="settings-item">
                        <span class="settings-item-label">メールアドレス</span>
                        <span class="settings-item-value">user@example.com</span>
                    </div>
                    <div class="settings-item">
                        <span class="settings-item-label">パスワード変更</span>
                        <span class="settings-item-value"><span class="arrow">›</span></span>
                    </div>
                </div>
            ` : `
                <div class="text-center" style="padding: 40px 20px;">
                    <p style="color: #666; margin-bottom: 16px;">ログインすると設定を変更できます</p>
                    <button class="btn-primary" onclick="document.getElementById('login-modal').classList.remove('hidden')">
                        ログインする
                    </button>
                </div>
            `}

            <div class="settings-section">
                <div class="settings-section-title">サポート</div>
                <div class="settings-item">
                    <span class="settings-item-label">ヘルプ</span>
                    <span class="settings-item-value"><span class="arrow">›</span></span>
                </div>
                <div class="settings-item">
                    <span class="settings-item-label">利用規約</span>
                    <span class="settings-item-value"><span class="arrow">›</span></span>
                </div>
                <div class="settings-item">
                    <span class="settings-item-label">プライバシーポリシー</span>
                    <span class="settings-item-value"><span class="arrow">›</span></span>
                </div>
            </div>

            <a href="#" class="help-link" style="color: #c62828;">
                ギャンブル依存症相談窓口
            </a>

            ${state.isLoggedIn ? `
                <button class="btn-secondary btn-full" style="margin: 0 16px; width: calc(100% - 32px);" onclick="doLogout()">
                    ログアウト
                </button>
            ` : ''}
        </div>
    `;
}

function editLimit() {
    const newLimit = prompt('新しい負け額限度額を入力してください（現在: ¥' + state.userLimit.toLocaleString() + '）', state.userLimit);
    if (newLimit && !isNaN(newLimit)) {
        const limit = parseInt(newLimit);
        if (limit < state.userLimit) {
            state.userLimit = limit;
            alert('負け額限度額を ¥' + limit.toLocaleString() + ' に変更しました。');
        } else if (limit > state.userLimit) {
            alert('増額のリクエストを受け付けました。\n7日後に反映されます。');
        }
        renderSettings();
    }
}

function showRegister() {
    alert('新規登録画面（実装予定）');
}

// ========== カート機能 ==========

function addToCart() {
    if (!isValidHorseSelection()) {
        alert('必要な頭数を選択してください');
        return;
    }

    const numbers = state.selectedHorses.sort((a, b) => a - b).join('-');

    state.cart.push({
        race: { ...state.selectedRace },
        type: state.betData.type,
        numbers: numbers,
        amount: state.betData.amount
    });

    // 選択をリセット
    state.selectedHorses = [];
    state.betData.amount = 1000;

    updateCartBadge();

    // トースト表示
    showToast('カートに追加しました');

    // レース詳細を再描画（カートボタン表示更新）
    renderRaceDetail();
}

function removeFromCart(index) {
    state.cart.splice(index, 1);
    updateCartBadge();
    renderCart();
}

function clearCart() {
    if (confirm('カートの中身をすべて削除しますか？')) {
        state.cart = [];
        updateCartBadge();
        renderCart();
    }
}

function updateCartBadge() {
    const badge = document.getElementById('cart-badge');
    if (badge) {
        if (state.cart.length > 0) {
            badge.textContent = state.cart.length;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
}

function showToast(message) {
    // 既存のトーストを削除
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: #333;
        color: white;
        padding: 12px 24px;
        border-radius: 24px;
        font-size: 14px;
        z-index: 1000;
        animation: fadeIn 0.3s ease;
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

function showCart() {
    state.currentPage = 'cart';
    state.selectedRace = null;
    renderCart();
}

function renderCart() {
    const main = document.getElementById('main-content');
    const totalAmount = state.cart.reduce((sum, item) => sum + item.amount, 0);
    const remainingLimit = state.userLimit - state.currentLoss;
    const isOverLimit = totalAmount > remainingLimit && state.isLoggedIn;

    main.innerHTML = `
        <div class="fade-in">
            <button class="back-btn" onclick="goBackFromCart()">← レース一覧に戻る</button>

            <div class="cart-container">
                <div class="cart-header">
                    <h3>🛒 カート</h3>
                    ${state.cart.length > 0 ? `
                        <button class="cart-clear-btn" onclick="clearCart()">すべて削除</button>
                    ` : ''}
                </div>

                ${state.cart.length === 0 ? `
                    <div class="cart-empty">
                        <div class="cart-empty-icon">🛒</div>
                        <p>カートに馬券がありません</p>
                        <p style="font-size: 12px; margin-top: 8px;">レースを選んで買い目を追加しましょう</p>
                    </div>
                ` : `
                    ${state.cart.map((item, index) => `
                        <div class="cart-item">
                            <div class="cart-item-info">
                                <div class="cart-item-race">${item.race.venue} ${item.race.number} ${item.race.name}</div>
                                <div class="cart-item-bet">${item.type} ${item.numbers}</div>
                                <div class="cart-item-amount">¥${item.amount.toLocaleString()}</div>
                            </div>
                            <button class="cart-item-delete" onclick="removeFromCart(${index})">×</button>
                        </div>
                    `).join('')}

                    <div class="cart-summary">
                        <div class="cart-summary-row">
                            <span>買い目数</span>
                            <span>${state.cart.length}点</span>
                        </div>
                        <div class="cart-summary-row total">
                            <span>合計金額</span>
                            <span>¥${totalAmount.toLocaleString()}</span>
                        </div>
                        ${state.isLoggedIn ? `
                            <div class="cart-summary-row ${isOverLimit ? 'danger' : remainingLimit < 5000 ? 'warning' : ''}">
                                <span>残り許容負け額</span>
                                <span>¥${remainingLimit.toLocaleString()}</span>
                            </div>
                            ${isOverLimit ? `
                                <div class="cart-summary-row danger" style="font-size: 12px;">
                                    <span>⚠ 合計金額が負け額限度額を超えています</span>
                                </div>
                            ` : ''}
                        ` : ''}
                    </div>
                `}
            </div>

            ${state.cart.length > 0 ? `
                <button class="add-more-btn" onclick="goBackFromCart()">
                    ＋ 別のレースの買い目を追加
                </button>

                <button class="ai-consult-btn" onclick="startBulkAIConsult()">
                    🤖 まとめてAIに相談する
                </button>
            ` : `
                <button class="btn-primary" style="width: 100%;" onclick="goBackFromCart()">
                    レースを選ぶ
                </button>
            `}
        </div>
    `;
}

function goBackFromCart() {
    state.currentPage = 'races';
    state.selectedRace = null;
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelector('[data-page="races"]').classList.add('active');
    renderPage('races');
}

function startBulkAIConsult() {
    if (state.cart.length === 0) {
        alert('カートに買い目がありません');
        return;
    }

    renderBulkAIChat();
}

function renderBulkAIChat() {
    const main = document.getElementById('main-content');
    const totalAmount = state.cart.reduce((sum, item) => sum + item.amount, 0);
    const remainingLimit = state.userLimit - state.currentLoss;
    const isOverLimit = totalAmount > remainingLimit && state.isLoggedIn;

    // 各買い目のモックデータフィードバックを生成
    const betFeedbacks = state.cart.map(item => {
        const horseNumbers = item.numbers.split('-').map(n => parseInt(n));
        return {
            ...item,
            odds: (Math.random() * 30 + 5).toFixed(1),
            horseDetails: horseNumbers.map(num => {
                const horse = horses.find(h => h.number === num);
                return horse ? {
                    number: num,
                    name: horse.name,
                    analysis: getRandomAnalysis()
                } : { number: num, name: '不明', analysis: '-' };
            })
        };
    });

    main.innerHTML = `
        <div class="fade-in">
            <button class="back-btn" onclick="goBackToCart()">← カートに戻る</button>

            <div class="ai-chat-container">
                <div class="ai-chat-header">
                    <div class="ai-avatar">🤖</div>
                    <div class="ai-chat-header-text">
                        <h3>馬券会議 AI</h3>
                        <p>立ち止まって、考えましょう</p>
                    </div>
                </div>

                <div class="chat-messages">
                    <div class="chat-message ai">
                        <div class="message-bubble">
                            ${state.cart.length}件の買い目について分析しました。<br>
                            以下のデータを参考に、最終判断はあなた自身で行いましょう。
                        </div>
                    </div>
                </div>

                <div class="data-feedback">
                    <div class="feedback-title">📊 買い目データフィードバック</div>

                    ${betFeedbacks.map(bet => `
                        <div class="bet-feedback-card">
                            <div class="bet-feedback-header">
                                <span class="bet-feedback-race">${bet.race.venue} ${bet.race.number}</span>
                                <span class="bet-feedback-type">${bet.type} ${bet.numbers}</span>
                                <span class="bet-feedback-odds">予想オッズ ${bet.odds}倍</span>
                            </div>
                            ${bet.horseDetails.map(h => `
                                <div class="feedback-item">
                                    <span class="feedback-label">${h.number}番 ${h.name}</span>
                                    <span class="feedback-value">${h.analysis}</span>
                                </div>
                            `).join('')}
                            <div class="feedback-item">
                                <span class="feedback-label">掛け金</span>
                                <span class="feedback-value">¥${bet.amount.toLocaleString()}</span>
                            </div>
                        </div>
                    `).join('')}

                    <div class="feedback-summary">
                        <div class="feedback-item total">
                            <span class="feedback-label">合計掛け金</span>
                            <span class="feedback-value">¥${totalAmount.toLocaleString()}</span>
                        </div>
                        ${state.isLoggedIn ? `
                            <div class="feedback-item ${remainingLimit < 5000 ? 'warning' : ''}">
                                <span class="feedback-label">残り許容負け額</span>
                                <span class="feedback-value">¥${remainingLimit.toLocaleString()}</span>
                            </div>
                            ${isOverLimit ? `
                                <div class="feedback-item danger">
                                    <span class="feedback-label">⚠ 限度額超過</span>
                                    <span class="feedback-value negative">-¥${(totalAmount - remainingLimit).toLocaleString()}</span>
                                </div>
                            ` : ''}
                        ` : ''}
                    </div>
                </div>

                <div class="action-buttons">
                    ${state.isLoggedIn ? `
                        <button class="btn-primary" ${isOverLimit ? 'disabled' : ''} onclick="purchaseAll()">
                            ${isOverLimit ? '限度額超過' : 'すべて購入する'}
                        </button>
                    ` : `
                        <button class="btn-primary" onclick="showLoginPrompt()">
                            ログインして購入
                        </button>
                    `}
                    <button class="btn-secondary" onclick="goBackToCart()">やめておく</button>
                </div>
            </div>
        </div>
    `;
}

function getRandomAnalysis() {
    const analyses = [
        '前走1着 / コース◎',
        '前走3着 / 長距離○',
        '前走5着 / 休み明け△',
        '前走2着 / 騎手◎',
        '前走4着 / 馬場△',
        '前走1着 / 実績◎',
        '前走6着 / 調子↓',
        '前走2着 / 相性○',
    ];
    return analyses[Math.floor(Math.random() * analyses.length)];
}

function goBackToCart() {
    state.chatMessages = [];
    renderCart();
}

function purchaseAll() {
    const totalAmount = state.cart.reduce((sum, item) => sum + item.amount, 0);
    const details = state.cart.map(item =>
        `${item.race.number} ${item.type} ${item.numbers} ¥${item.amount.toLocaleString()}`
    ).join('\n');

    alert(`${state.cart.length}件の馬券を購入しました！\n\n${details}\n\n合計: ¥${totalAmount.toLocaleString()}`);

    state.currentLoss += totalAmount;
    state.cart = [];
    state.chatMessages = [];
    updateCartBadge();
    goBackFromCart();
}
